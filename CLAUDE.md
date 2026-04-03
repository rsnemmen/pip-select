# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`pip-select` is a single-file Python CLI (`pip-select.py`) for interactively upgrading pip-installed packages while excluding conda-installed ones. No external dependencies — standard library only.

## Validation Commands

```bash
# Syntax check
python3 -m py_compile pip-select.py

# Verify CLI contract
python3 pip-select.py --help

# Behavior smoke test (hits network, no installs)
python3 pip-select.py --dry-run --no-curses
```

Optional linting (not required, not configured in the repo):
```bash
ruff check pip-select.py
black --check pip-select.py
mypy pip-select.py
```

## Architecture

All logic lives in `pip-select.py`. The flow is:

1. **Conda detection** (`detect_conda_prefix`, `conda_meta_names`) — finds conda prefix via `CONDA_PREFIX` env var or `sys.prefix/conda-meta`
2. **Package classification** (`pip_installed_set_excluding_conda`) — uses two signals: `INSTALLER` metadata file (primary) and `conda-meta/*.json` (secondary); unknown installers are treated as pip-like
3. **Outdated discovery** (`get_upgrade_candidates_from_pip`) — runs `sys.executable -m pip list --outdated --format=json` in a background thread while animating a time-based progress bar
4. **Selection UI** — `curses_select` (default when TTY) or `fallback_select` (text, `--no-curses`)
5. **Upgrade execution** (`upgrade_selected`) — runs `sys.executable -m pip install --upgrade <pkg>==<latest>`

Key subprocess helper: `_base_env()` sets `PIP_DISABLE_PIP_VERSION_CHECK=1` — reuse it for all pip-related subprocesses.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success or no upgradeable packages |
| `1` | pip subprocess error or upgrade interrupted |
| `2` | `--user` inside venv, cancelled selection, or user declined upgrade |

## Code Style

- `from __future__ import annotations`
- Standard library only — do not add external dependencies
- Type hints using `Optional`, `List`, `Dict`, `Set`, `Tuple`, `Sequence`
- `@dataclass(frozen=True)` for records (`InstalledDist`, `UpgradeCandidate`)
- Double-quoted strings
- Section headers: `# ----------------------------\n# Section Name\n# ----------------------------`
- Python 3.8+ compatibility required

## Key Constraints

- Single-file structure — do not split into a package unless explicitly asked
- Keep both curses UI and text fallback working
- Always use `sys.executable -m pip`, never a hardcoded `pip` binary
- Note: `import pip-select` won't work (hyphen in filename) — subprocess-based testing is safer
- Update `README.md` when user-visible behavior changes (flags, selection, conda filtering)
- Update `AGENTS.md` when repo structure or validation flow changes
