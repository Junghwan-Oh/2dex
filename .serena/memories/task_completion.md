# Task Completion Checklist

## Before Marking Complete

### 1. Code Quality
- [ ] Run formatter: `black . && ruff format .`
- [ ] Run linter: `ruff check . --fix`
- [ ] Run type check: `mypy perpdex/` (if applicable)

### 2. Testing
- [ ] Run tests: `pytest -v`
- [ ] Check coverage: `pytest --cov`
- [ ] Add tests for new functionality

### 3. Documentation
- [ ] Update docstrings if needed
- [ ] Update README if API changed
- [ ] Add inline comments for complex logic

### 4. Git
- [ ] Check status: `git status`
- [ ] Review changes: `git diff`
- [ ] Create meaningful commit message
- [ ] Commit: `git add . && git commit -m "descriptive message"`

### 5. Cleanup
- [ ] Remove debug prints/logs
- [ ] Remove unused imports
- [ ] Remove temporary files
