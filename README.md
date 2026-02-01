# `pip-select`: Interactive command-line tool for upgrading pip-installed packages

An interactive, user-friendly tool for upgrading pip-installed packages while smartly excluding conda-installed ones. No more accidental upgrades of your carefully managed conda packages!

## Installation

Simply download the script and make it executable:

```bash
# Download the script
curl -O https://raw.githubusercontent.com/yourusername/pip-select-upgrade/main/pip-select.py

# Make it executable
chmod +x pip-select.py

# Optional: Move to your PATH
mv pip-select.py ~/.local/bin/pip-select-upgrade
```

Or run it directly without installing:

```bash
python pip-select.py
```

## Usage

### Quick Start (Dry Run)

See what packages are available for upgrade without actually upgrading:

```bash
python pip-select.py --dry-run --no-curses
```

**Output:**

```
Conda environment detected at: /home/user/miniconda3/envs/myenv
Detected 84 pip-installed packages (excluded 141 conda-installed).
Checking 84 packages [████████████████████████████░░] 87%

Upgradeable packages:
    1. aiohttp                        3.13.2       -> 3.13.3      
    2. beartype                       0.14.1       -> 0.22.9      
    3. datasets                       4.4.2        -> 4.5.0       
    4. dill                           0.4.0        -> 0.4.1       
    5. numpy                          1.24.0       -> 2.0.0       
    ...

Enter numbers to upgrade (e.g. 1 3 4), or blank to cancel: 
```

### Interactive Mode (Curses UI)

Launch the beautiful interactive menu:

```bash
./pip-select.py
```

**Screenshot:**

```
SPACE=toggle  ↑/↓/PgUp/PgDn=move  Home/End=jump  a=all  n=none  Enter=upg  q=quit  Selected: 3/84
[ ] aiohttp                         3.13.2       -> 3.13.3      
[ ] beartype                        0.14.1       -> 0.22.9      
[x] datasets                        4.4.2        -> 4.5.0       
[ ] dill                            0.4.0        -> 0.4.1       
[ ] dol                             0.3.37       -> 0.3.38      
[x] numpy                           1.24.0       -> 2.0.0       
[x] pandas                          2.0.0        -> 2.2.0       
[ ] requests                        2.28.0       -> 2.31.0      
```

Navigate with arrow keys, toggle with spacebar, and press Enter to upgrade selected packages!

### User Mode Installation

If you don't have admin rights, use the `--user` flag:

```bash
python pip-select.py --user
```

This will install upgrades to your user site-packages directory.

## Keyboard Shortcuts

When in the interactive curses mode:

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move up/down one item |
| `k` / `j` | Vim-style up/down |
| `PgUp` / `PgDn` | Move up/down one page |
| `Home` / `g` | Jump to first item |
| `End` | Jump to last item |
| `Space` | Toggle selection |
| `a` | Select all packages |
| `n` | Select none (clear all) |
| `Enter` | Upgrade selected packages |
| `q` | Quit without upgrading |

## Features

- **Smart Conda Detection**: Automatically detects and excludes packages installed via conda
- **Visual Progress Bar**: See exactly what's happening with a tqdm-style progress indicator
- **Interactive Selection**: Multi-select menu with spacebar toggle (vim-style keybindings included!)
- **Curses UI**: Beautiful terminal interface with keyboard navigation
- **Text Fallback**: Works even without curses support
- **Safe Dry-Run**: Preview upgrades before committing
- **Zero Dependencies**: Uses only Python standard library
- **User Mode Support**: Install to user site-packages when you don't have admin rights

## Requirements

- **Python**: 3.8 or higher
- **OS**: Linux or macOS (uses curses for the interactive UI)
- **pip**: Any recent version
- **Conda**: Optional (tool works great with or without it!)

## Command Line Options

```
usage: pip-select.py [-h] [--user] [--dry-run] [--no-curses] ...

Interactive upgrader for pip-installed packages (excluding conda-installed).

positional arguments:
  pip_args     Extra args passed to pip install (use '--' before them), e.g.
               -- --constraint constraints.txt

options:
  -h, --help   show this help message and exit
  --user       Use 'pip install --user' (recommended if you don't have
               permission to modify system site-packages).
  --dry-run    Show what would be upgraded, but do not run pip install.
  --no-curses  Disable curses UI (use text fallback selection).
```

## How It Works

The tool uses two clever methods to detect conda-installed packages:

1. **INSTALLER Metadata**: Checks the `INSTALLER` file in package metadata (modern packages record how they were installed)
2. **Conda-Meta Directory**: Scans `conda-meta/*.json` files in your conda environment

This dual approach ensures conda packages are reliably excluded from the upgrade list, even in mixed environments.

## Additional Examples

### Using with Constraints File

Upgrade packages while respecting version constraints:

```bash
python pip-select.py -- --constraint constraints.txt
```

### Upgrade Specific Index

Use a different package index:

```bash
python pip-select.py -- --index-url https://pypi.example.com/simple
```

### Combining Options

Dry-run in user mode with custom index:

```bash
python pip-select.py --dry-run --user -- --index-url https://pypi.org/simple
```

### Help Menu

View all available options:

```bash
python pip-select.py --help
```

## Tips & Notes

- **Virtual Environments**: Works great in venv, virtualenv, and conda envs
- **No Curses?**: Use `--no-curses` for a simple text-based interface
- **Safety First**: Always use `--dry-run` first to preview changes
- **Conda Environments**: Tool auto-detects conda and shows the environment path
- **Windows**: Sorry, this tool is Linux/macOS only due to curses dependency
- **Dependency Free**: No pip-review or other tools needed - uses pip directly!

## Troubleshooting

**"--user cannot be used inside a virtual environment"**
→ Omit the `--user` flag when running inside a venv

**"No upgradeable pip-installed packages found"**
→ All your pip packages are up to date, or they're all conda-installed

**Progress bar freezes**
→ This is normal! The bar is time-based. pip is still working in the background checking PyPI.

## License

This project is open source. Feel free to use, modify, and share!

---

**Happy upgrading!**
