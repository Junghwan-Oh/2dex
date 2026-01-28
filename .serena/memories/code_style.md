# Code Style and Conventions

## Naming Conventions
- **Variables**: camelCase (per user preference in CLAUDE.md)
- **Functions**: snake_case (Python standard)
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE

## Type Hints
- Use type hints for function parameters and return values
- Use `from typing import ...` for complex types

## Docstrings
- Use Google-style docstrings
- Document parameters, returns, and exceptions

## Code Formatting
- **Formatter**: black (line length 88)
- **Linter**: ruff
- **Type Checker**: mypy

## Import Order
1. Standard library
2. Third-party packages
3. Local modules

## Error Handling
- Use specific exceptions
- Log errors appropriately
- Use asyncio exception handling for async code

## Testing
- Test files: `test_*.py` or `*_test.py`
- Use pytest fixtures for setup
- Aim for ≥80% coverage
