# Agent Instructions for pip_select_upgrade

This is a single-file Python CLI tool for interactively upgrading pip packages while excluding conda-installed packages.

## Project Structure

- `pip_select_upgrade.py` - Main CLI script (548 lines, dependency-free)
- No external dependencies (uses only Python standard library)
- Supports Python 3.8+
- Linux/macOS only (uses curses)

## Build/Lint/Test Commands

### Linting
```bash
# Run ruff for linting
ruff check pip_select_upgrade.py

# Run ruff with auto-fix
ruff check --fix pip_select_upgrade.py
```

### Formatting
```bash
# Format with black
black pip_select_upgrade.py

# Check formatting without changes
black --check pip_select_upgrade.py
```

### Type Checking
```bash
# Run mypy for type checking
mypy pip_select_upgrade.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest test_pip_select_upgrade.py

# Run single test function
pytest test_pip_select_upgrade.py::test_function_name

# Run with verbose output
pytest -xvs test_pip_select_upgrade.py::test_function_name
```

### Running the Script
```bash
# Dry run mode (no actual upgrades)
python pip_select_upgrade.py --dry-run --no-curses

# Help
python pip_select_upgrade.py --help
```

## Code Style Guidelines

### General Style
- Follow PEP 8 conventions
- Use `black` for formatting (88 character line length)
- Use type hints for all function signatures
- Add docstrings for all public functions and classes

### Imports
- Group imports in this order:
  1. Standard library imports (alphabetical)
  2. Third-party imports (alphabetical)  
  3. Local imports (alphabetical)
- Use `from __future__ import annotations` for Python 3.8+ type hint compatibility
- Use conditional imports for optional dependencies with try/except

Example:
```python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Optional

try:
    from importlib import metadata as importlib_metadata
except Exception:
    import importlib_metadata  # type: ignore
```

### Naming Conventions
- Functions: `snake_case` (e.g., `get_upgrade_candidates()`)
- Classes: `PascalCase` (e.g., `UpgradeCandidate`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `_NAME_NORM_RE`)
- Private functions: `_leading_underscore` (e.g., `_show_progress_bar()`)
- Type variables: Use `TypeVar` with descriptive names

### Type Hints
- Use Python 3.8+ style with `from __future__ import annotations`
- Annotate all function parameters and return types
- Use `Optional[Type]` for nullable values
- Use `List[Type]`, `Dict[KeyType, ValueType]` from typing module
- Use `Sequence` for read-only collections, `List` for mutable

Example:
```python
def parse_packages(data: str) -> List[UpgradeCandidate]:
    """Parse package data and return candidates."""
    result: List[UpgradeCandidate] = []
    return result
```

### Error Handling
- Use specific exceptions when possible
- Handle errors gracefully with try/except blocks
- Print user-friendly error messages to stderr
- Use `raise SystemExit(code)` for fatal errors with appropriate exit codes:
  - 0: Success
  - 1: General error
  - 2: User cancellation or usage error

Example:
```python
try:
    data = json.loads(output)
except json.JSONDecodeError as e:
    print(f"Error parsing JSON: {e}", file=sys.stderr)
    raise SystemExit(1)
```

### Documentation
- Use triple-quoted docstrings for all modules, classes, and functions
- Follow Google-style docstrings:
```python
def function_name(param: str) -> int:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        SystemExit: When error occurs
    """
```

### Code Organization
- Use section comments with consistent formatting:
```python
# ----------------------------
# Section Name
# ----------------------------
```
- Group related functions together
- Keep functions focused and single-purpose
- Maximum function length: ~50 lines
- Use dataclasses for data containers

### String Formatting
- Use f-strings for all string formatting
- Use double quotes for strings consistently
- Use raw strings (r"") for regex patterns

Example:
```python
line = f"{mark} {c.name}  {c.current} -> {c.latest}"
pattern = re.compile(r"[-_.]+")
```

### Subprocess Handling
- Always use `subprocess.run()` with proper error handling
- Capture stdout/stderr when needed
- Use `text=True` for string output
- Check return codes and handle failures

Example:
```python
result = subprocess.run(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    check=False
)
if result.returncode != 0:
    handle_error(result.stderr)
```

### Testing Guidelines
- Write tests using pytest
- Use descriptive test function names: `test_what_is_being_tested()`
- Use fixtures for common setup
- Mock external dependencies (subprocess calls)
- Test both success and error cases

Example:
```python
def test_parse_pip_list_json():
    """Test parsing pip list JSON output."""
    json_data = '[{"name": "pkg", "version": "1.0", "latest_version": "2.0"}]'
    result = parse_pip_list_outdated_json(json_data)
    assert len(result) == 1
    assert result[0].name == "pkg"
```

## Pre-commit Checklist

Before committing changes:
1. Run `ruff check pip_select_upgrade.py`
2. Run `black --check pip_select_upgrade.py`
3. Run `mypy pip_select_upgrade.py` (if type checker is configured)
4. Run `python -m py_compile pip_select_upgrade.py` for syntax check
5. Test the script: `python pip_select_upgrade.py --dry-run --no-curses`
6. Ensure docstrings are updated for modified functions

## Notes for Agents

- This is a CLI tool - maintain backward compatibility for command-line interface
- No external dependencies allowed (standard library only)
- Preserve the dependency-free nature of the script
- Linux/macOS only - curses is not available on Windows
- Always test with `--dry-run` flag to avoid accidental package upgrades
- Keep the single-file structure - don't split into modules
