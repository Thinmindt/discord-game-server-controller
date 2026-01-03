# Development Guide

This document covers the development setup, tooling, and workflow for contributing to the project.

## Environment Setup

### Activate Virtual Environment

**Windows (PowerShell):**

```powershell
.venv\Scripts\activate
```

**Windows (Command Prompt):**

```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac:**

```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r dependencies/requirements.txt
pip install -r dependencies/dev-requirements.txt
```

## Code Quality Tools

All tool configurations are stored in `pyproject.toml`. Run these commands from the project root with the virtual environment activated.

### Formatting & Linting (Ruff)

Format all Python files:

```bash
ruff format .
```

Check formatting without making changes:

```bash
ruff format . --check
```

Run linter on all files:

```bash
ruff check .
```

Run linter with auto-fix:

```bash
ruff check . --fix
```

**Configuration:** Line length 100, Python 3.14 target. Includes import sorting, style checks, and common bug detection.

### Type Checking (Mypy)

Run strict type checking:

```bash
mypy .
```

**Configuration:** Strict mode enabled, test files excluded, missing imports ignored.

## Testing

### Run All Tests

```bash
pytest
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest test/test_backup_manager.py
```

### Run Tests with Coverage

```bash
pytest --cov=src
```

**Configuration:** Test discovery looks in `test/` directory and root for `test_*.py` files.
