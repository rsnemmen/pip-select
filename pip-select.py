#!/usr/bin/env python3
"""
pip-select.py

Interactive multi-select upgrader for pip-installed packages (excluding conda-installed).

Features:
  1) Detect packages installed via pip (excludes conda-installed packages)
  2) Lists outdated packages directly via pip (no external dependencies)
  3) Displays upgradeable packages with old/new versions
  4) Interactive menu (space toggles, enter confirms; multiple selection)
  5) Upgrades selected packages via pip

Works on Linux/macOS (uses curses).
"""

from __future__ import annotations

import argparse
import curses
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    # Python 3.8+
    from importlib import metadata as importlib_metadata
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore


# ----------------------------
# Helpers: normalization / IO
# ----------------------------

_NAME_NORM_RE = re.compile(r"[-_.]+")


def norm_name(name: str) -> str:
    # PEP 503-like normalization: collapse [-_.] to "-"
    return _NAME_NORM_RE.sub("-", name).lower().strip()


def run_capture(cmd: Sequence[str], env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    p = subprocess.run(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    return p.returncode, p.stdout, p.stderr


def run_stream(cmd: Sequence[str], env: Optional[Dict[str, str]] = None) -> int:
    p = subprocess.run(list(cmd), env=env)
    return p.returncode


def ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    suffix = " [y/N] " if default_no else " [Y/n] "
    while True:
        try:
            ans = input(prompt + suffix).strip().lower()
        except EOFError:
            return False if default_no else True

        if not ans:
            return False if default_no else True
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please answer y or n.")


def is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def in_venv() -> bool:
    return getattr(sys, "base_prefix", sys.prefix) != sys.prefix


# ----------------------------
# Conda detection / exclusion
# ----------------------------

def detect_conda_prefix() -> Optional[Path]:
    # Common indicator
    cp = os.environ.get("CONDA_PREFIX")
    if cp:
        p = Path(cp)
        if p.exists():
            return p

    # Heuristic: sys.prefix contains conda-meta
    p = Path(sys.prefix)
    if (p / "conda-meta").is_dir():
        return p

    return None


def conda_meta_names(conda_prefix: Path) -> Set[str]:
    """
    Return a set of conda package names (normalized) from conda-meta/*.json.
    Note: conda package names may not match PyPI names perfectly, so we use
    this only as a *secondary* exclusion signal.
    """
    meta_dir = conda_prefix / "conda-meta"
    names: Set[str] = set()
    if not meta_dir.is_dir():
        return names

    for jf in meta_dir.glob("*.json"):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            n = data.get("name")
            if isinstance(n, str) and n.strip():
                names.add(norm_name(n))
        except Exception:
            continue
    return names


# ----------------------------
# Installed package inventory
# ----------------------------

@dataclass(frozen=True)
class InstalledDist:
    name: str          # display/original
    version: str
    installer: str     # "pip", "conda", "", etc.


def read_installer(dist) -> str:
    try:
        txt = dist.read_text("INSTALLER")
        return (txt or "").strip().lower()
    except Exception:
        return ""


def list_installed_distributions() -> List[InstalledDist]:
    out: List[InstalledDist] = []
    for dist in importlib_metadata.distributions():
        try:
            name = dist.metadata.get("Name") or dist.metadata.get("name")  # type: ignore[attr-defined]
            if not name:
                continue
            name = str(name).strip()
            if not name:
                continue
            out.append(
                InstalledDist(
                    name=name,
                    version=str(getattr(dist, "version", "") or ""),
                    installer=read_installer(dist),
                )
            )
        except Exception:
            continue
    return out


def pip_installed_set_excluding_conda() -> Tuple[Set[str], int, int, Optional[Path]]:
    """
    Returns:
      - set of normalized names considered 'pip-installed'
      - count_pip
      - count_excluded_conda
      - conda_prefix (or None)
    """
    conda_prefix = detect_conda_prefix()
    conda_names = conda_meta_names(conda_prefix) if conda_prefix else set()

    dists = list_installed_distributions()

    pip_names: Set[str] = set()
    excluded_conda = 0

    for d in dists:
        n = norm_name(d.name)

        # Primary signal: INSTALLER metadata
        if d.installer == "conda":
            excluded_conda += 1
            continue

        # Secondary signal: conda-meta (only if we are in a conda prefix)
        if conda_prefix and n in conda_names:
            excluded_conda += 1
            continue

        # Consider it pip-installed if installer says pip OR installer is unknown.
        # (Some environments may lack INSTALLER; unknown is treated as pip unless clearly conda.)
        if d.installer in {"pip", "pip3", ""}:
            pip_names.add(n)
        else:
            # Other installers (e.g., "uv") are treated as pip-like by default.
            pip_names.add(n)

    return pip_names, len(pip_names), excluded_conda, conda_prefix


# ----------------------------
# pip-review integration
# ----------------------------

@dataclass(frozen=True)
class UpgradeCandidate:
    name: str
    current: str
    latest: str
    dist_type: str = ""


def _base_env() -> Dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def parse_pip_list_outdated_json(output: str) -> List[UpgradeCandidate]:
    """
    Parses JSON output from 'pip list --outdated --format=json'.
    Format: [{"name": "pkg", "version": "1.0", "latest_version": "2.0"}, ...]
    """
    cands: List[UpgradeCandidate] = []
    if not output.strip():
        return cands
    
    try:
        data = json.loads(output)
        if not isinstance(data, list):
            return cands
        
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            current = item.get("version")
            latest = item.get("latest_version")
            if name and current and latest:
                cands.append(UpgradeCandidate(
                    name=str(name),
                    current=str(current),
                    latest=str(latest),
                    dist_type=""
                ))
    except json.JSONDecodeError:
        pass
    
    return cands


def _show_progress_bar(total_packages: int, stop_event: threading.Event) -> None:
    """Animate a tqdm-style progress bar while checking for outdated packages."""
    start_time = time.time()
    # Estimate ~0.1s per package for the check, minimum 3 seconds
    estimated_seconds = max(total_packages * 0.1, 3)
    bar_width = 30
    
    while not stop_event.is_set():
        elapsed = time.time() - start_time
        # Calculate percentage based on elapsed vs estimated time
        pct = min(100, int((elapsed / estimated_seconds) * 100))
        
        # Build progress bar with smooth fill
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Show progress
        print(f"\rChecking {total_packages} packages [{bar}] {pct}%", end="", flush=True)
        time.sleep(0.05)  # Update 20 times per second for smooth animation
    
    # Fill to 100% when done
    bar = "█" * bar_width
    print(f"\rChecking {total_packages} packages [{bar}] 100%", end="", flush=True)
    time.sleep(0.1)
    # Clear the line when done
    print("\r" + " " * 80 + "\r", end="")


def get_upgrade_candidates_from_pip(total_packages: int) -> List[UpgradeCandidate]:
    """Get outdated packages directly from pip with progress bar."""
    stop_event = threading.Event()
    result_container = {}
    
    def run_pip():
        """Run pip command in background thread."""
        cmd = [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"]
        rc, out, err = run_capture(cmd, env=_base_env())
        result_container['rc'] = rc
        result_container['out'] = out
        result_container['err'] = err
        stop_event.set()  # Signal that pip is done
    
    # Start pip command in background thread
    pip_thread = threading.Thread(target=run_pip)
    pip_thread.start()
    
    # Show progress bar while waiting
    _show_progress_bar(total_packages, stop_event)
    
    # Wait for pip thread to complete
    pip_thread.join()
    
    # Check results
    rc = result_container.get('rc', 1)
    out = result_container.get('out', '')
    err = result_container.get('err', '')
    
    if rc != 0:
        msg = (err or "").strip()
        if msg:
            print(msg)
        raise SystemExit(rc)

    cands = parse_pip_list_outdated_json(out)
    return cands


# ----------------------------
# UI: curses multi-select menu
# ----------------------------

def curses_select(cands: List[UpgradeCandidate]) -> Optional[List[UpgradeCandidate]]:
    selected = [False] * len(cands)
    pos = 0
    top = 0

    def clamp(n: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, n))

    def _ui(stdscr) -> Optional[List[UpgradeCandidate]]:
        nonlocal pos, top, selected

        curses.curs_set(0)
        stdscr.keypad(True)

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            body_h = max(1, h - 2)

            # Keep pos visible
            pos = clamp(pos, 0, len(cands) - 1)
            if pos < top:
                top = pos
            if pos >= top + body_h:
                top = pos - body_h + 1
            top = clamp(top, 0, max(0, len(cands) - body_h))

            # Header
            chosen = sum(1 for x in selected if x)
            header = "SPACE=toggle  ↑/↓/PgUp/PgDn=move  Home/End=jump  a=all  n=none  Enter=upg  q=quit"
            status = f"Selected: {chosen}/{len(cands)}"
            stdscr.addnstr(0, 0, header, w - 1)
            stdscr.addnstr(0, max(0, w - 1 - len(status)), status, w - 1)

            # Body
            for row in range(body_h):
                idx = top + row
                if idx >= len(cands):
                    break
                c = cands[idx]
                mark = "[x]" if selected[idx] else "[ ]"
                line = f"{mark} {c.name}  {c.current} -> {c.latest}"
                if idx == pos:
                    stdscr.attron(curses.A_REVERSE)
                    stdscr.addnstr(1 + row, 0, line, w - 1)
                    stdscr.attroff(curses.A_REVERSE)
                else:
                    stdscr.addnstr(1 + row, 0, line, w - 1)

            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q")):
                return None
            if ch in (curses.KEY_UP, ord("k"), ord("K")):
                pos = clamp(pos - 1, 0, len(cands) - 1)
            elif ch in (curses.KEY_DOWN, ord("j"), ord("J")):
                pos = clamp(pos + 1, 0, len(cands) - 1)
            elif ch == curses.KEY_PPAGE:
                # PageUp: move up by one screen
                pos = max(0, pos - body_h)
            elif ch == curses.KEY_NPAGE:
                # PageDown: move down by one screen
                pos = min(len(cands) - 1, pos + body_h)
            elif ch in (curses.KEY_HOME, ord("g")):
                # Home: jump to first item (g as vim-style alias)
                pos = 0
            elif ch == curses.KEY_END:
                # End: jump to last item
                pos = len(cands) - 1
            elif ch == ord(" "):
                selected[pos] = not selected[pos]
            elif ch in (ord("a"), ord("A")):
                selected = [True] * len(cands)
            elif ch in (ord("n"), ord("N")):
                selected = [False] * len(cands)
            elif ch in (curses.KEY_ENTER, 10, 13):
                chosen_items = [cands[i] for i, ok in enumerate(selected) if ok]
                return chosen_items

    return curses.wrapper(_ui)


def fallback_select(cands: List[UpgradeCandidate]) -> Optional[List[UpgradeCandidate]]:
    print("\nUpgradeable packages:")
    for i, c in enumerate(cands, start=1):
        print(f"  {i:>3}. {c.name:30} {c.current:12} -> {c.latest:12}")

    s = input("\nEnter numbers to upgrade (e.g. 1 3 4), or blank to cancel: ").strip()
    if not s:
        return None

    picks: Set[int] = set()
    for tok in s.replace(",", " ").split():
        if tok.isdigit():
            picks.add(int(tok))
    chosen = [cands[i - 1] for i in sorted(picks) if 1 <= i <= len(cands)]
    return chosen


# ----------------------------
# Upgrade execution
# ----------------------------

def upgrade_selected(
    chosen: List[UpgradeCandidate],
    pip_user: bool,
    extra_pip_args: List[str],
    dry_run: bool,
) -> int:
    if not chosen:
        print("No packages selected. Nothing to do.")
        return 0

    specs = [f"{c.name}=={c.latest}" for c in chosen]

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if pip_user:
        cmd.append("--user")
    cmd += specs
    cmd += extra_pip_args

    print("\nWill run:")
    print("  " + " ".join(cmd))
    if dry_run:
        print("\n--dry-run enabled: not executing pip.")
        return 0

    if not ask_yes_no("\nProceed with upgrade?", default_no=True):
        print("Cancelled.")
        return 2

    return run_stream(cmd, env=_base_env())


# ----------------------------
# Main
# ----------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Interactive upgrader for pip-installed packages (excluding conda-installed)."
    )
    ap.add_argument(
        "--user",
        action="store_true",
        help="Use 'pip install --user' (recommended if you don't have permission to modify system site-packages).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be upgraded, but do not run pip install.",
    )
    ap.add_argument(
        "--no-curses",
        action="store_true",
        help="Disable curses UI (use text fallback selection).",
    )
    ap.add_argument(
        "pip_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed to pip install (use '--' before them), e.g. -- --constraint constraints.txt",
    )

    args = ap.parse_args(argv)

    if args.user and in_venv():
        print("Error: --user cannot be used inside a virtual environment.")
        print("Tip: omit --user when running inside venv/pyenv/virtualenv.")
        return 2

    extra_pip_args = list(args.pip_args)
    if extra_pip_args and extra_pip_args[0] == "--":
        extra_pip_args = extra_pip_args[1:]

    pip_names, pip_count, excluded_conda, conda_prefix = pip_installed_set_excluding_conda()
    if conda_prefix:
        print(f"Conda environment detected at: {conda_prefix}")
    print(f"Detected {pip_count} pip-installed packages (excluded {excluded_conda} conda-installed).")

    all_cands = get_upgrade_candidates_from_pip(pip_count)

    # Filter to pip-installed (exclude conda-installed)
    cands = [c for c in all_cands if norm_name(c.name) in pip_names]

    if not cands:
        print("No upgradeable pip-installed packages found (excluding conda-installed).")
        return 0

    # Sort for stable menu
    cands.sort(key=lambda c: norm_name(c.name))

    if not args.no_curses and is_tty():
        chosen = curses_select(cands)
    else:
        chosen = fallback_select(cands)

    if chosen is None:
        print("Cancelled.")
        return 2

    return upgrade_selected(
        chosen=chosen,
        pip_user=args.user,
        extra_pip_args=extra_pip_args,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
