# YTM - YouTube Music CLI

## Build/Lint/Test Commands

```bash
pytest                               # Run test suite
pytest tests/test_specific.py        # Single test file
pytest -k "test_function"            # Single test function
pytest --cov=ytm_cli                 # With coverage
make test                            # Full test suite via Makefile
make test-quick                      # Quick tests (no coverage)
make lint                            # Lint with ruff
make format                          # Format with ruff
make check                           # Run all checks (lint + test)
```

## Code Style Guidelines

**Formatting & Linting:**
- 100-char line limit (ruff)
- Double quotes for strings
- 4 spaces indentation
- Python 3.8+ compatibility
- Type hints encouraged
- Use ruff for formatting and linting

**Import Style:**
- Group imports: stdlib, third-party, first-party
- Use isort rules (configured in ruff)
- `ytm_cli` is known-first-party

**Naming Conventions:**
- snake_case for functions and variables
- PascalCase for classes
- UPPER_CASE for constants

**Error Handling:**
- Keep it simple - avoid complex abstractions
- Test-first for bug fixes
- No secrets/credentials in code

## Key Technologies

- `ytmusicapi` - YouTube Music API
- `mpv` - Media player (system dependency)
- `rich` - Terminal formatting
- `curses` - Terminal UI (preferred for interactive UIs)

## Git Workflow

**Commit Format:** `<type>[optional scope]: <description>`
**Types:** feat, fix, chore, docs, refactor, test, style
**Before Committing:** `pytest && ruff check . && git diff --cached`

## Version Management

Version must be synced in `ytm_cli/__init__.py` and `pyproject.toml` (currently 0.5.0)

## Constraints

- DO NOT expose `auth.py` (in development, not functional)
- Keep it simple - avoid complex abstractions
- Test-first for bug fixes
- No secrets/credentials in code
