# Linting, Formatting, and Testing

## Linting
- **Primary tool**: Pylint (configured in GitHub Actions)
- **CI setup**: `.github/workflows/pylint.yml`
- **Python versions tested**: 3.8 and 3.13.5
- **Command**: `pylint $(git ls-files '*.py')`
- **Cache**: Ruff cache present (`.ruff_cache/`) suggesting ruff usage locally

## Testing
- **Status**: No test framework currently configured
- **Test files**: None present in the codebase
- **Recommendation**: Manual testing through application usage

## Formatting
- **No explicit formatter configured** (no black, isort, or other formatters found)
- **Style**: Manual adherence to Python conventions
- **Recommendation**: Consider adding black or ruff for consistent formatting

## Quality Assurance Workflow
1. **Local development**: Use ruff for linting (cache present)
2. **CI pipeline**: Pylint runs on push to repository
3. **Version management**: bump2version handles versioning
4. **Manual testing**: Test application features interactively

## Recommended Development Workflow
1. Make code changes
2. Run `pylint` on modified files locally
3. Test application functionality manually
4. Commit changes with conventional commit messages
5. Push to trigger CI pylint check

## Future Improvements
- Add pytest for automated testing
- Configure black or ruff for code formatting
- Add pre-commit hooks for quality checks
- Consider adding type checking with mypy