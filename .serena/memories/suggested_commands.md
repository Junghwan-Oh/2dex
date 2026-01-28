# Suggested Commands for DexBot Development

## Package Management
```bash
# Install dependencies
uv sync
uv pip install -r perpdex/requirements.txt

# Add new package
uv add <package-name>
```

## Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=perpdex --cov-report=html

# Run specific test file
pytest perpdex/tests/test_specific.py -v

# Run async tests
pytest -xvs --tb=short
```

## Code Quality
```bash
# Format code
black .
ruff format .

# Lint code
ruff check .
mypy perpdex/

# Format and lint
black . && ruff check . --fix
```

## Git Commands (Windows/MSYS2)
```bash
git status
git branch
git log --oneline -10
git diff
git add .
git commit -m "message"
```

## Run Trading Bots
```bash
# Run hedge bot (example)
cd perpdex/hedge
python hedge_mode.py

# Set PYTHONPATH if needed
PYTHONPATH="f:/Dropbox/dexbot:$PYTHONPATH" python script.py
```

## Utilities
```bash
# List files
ls -la

# Find files
find . -name "*.py" -type f

# Search in files
grep -r "pattern" --include="*.py"
rg "pattern" -t py
```
