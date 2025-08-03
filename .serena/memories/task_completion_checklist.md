# Task Completion Checklist

## When a coding task is completed, perform these steps:

### 1. Code Quality
- [ ] Run `pylint` on modified Python files
- [ ] Ensure code follows project conventions (see code_style_conventions.md)
- [ ] Verify imports are properly organized
- [ ] Check for proper docstrings on new functions/classes

### 2. Testing
- [ ] **Manual testing required** (no automated tests currently)
- [ ] Test the specific feature/fix implemented
- [ ] Test application startup: `python -m ytm_cli`
- [ ] Test core functionality: search, play, navigation
- [ ] Test authentication if auth-related changes made
- [ ] Test playlist functionality if playlist changes made

### 3. Configuration
- [ ] Update version in `ytm_cli/__init__.py` if needed
- [ ] Update `requirements.txt` if new dependencies added
- [ ] Update `CLAUDE.md` if new features or commands added

### 4. Documentation
- [ ] Update docstrings for new/modified functions
- [ ] Update command help text if CLI interface changed
- [ ] Consider updating README.md for user-facing changes

### 5. Git Workflow
- [ ] Use conventional commit messages (feat:, fix:, docs:, etc.)
- [ ] Check `git status` before committing
- [ ] Stage only relevant files with `git add`
- [ ] Write descriptive commit messages

### 6. CI/CD
- [ ] Ensure pylint CI check will pass
- [ ] Check that no sensitive information is committed
- [ ] Verify `.gitignore` covers new generated files

## Example Commands for Task Completion
```bash
# Quality check
pylint ytm_cli/modified_file.py

# Test the application
python -m ytm_cli "test song"

# Git workflow
git status
git add ytm_cli/modified_file.py
git commit -m "feat(feature): add new functionality"
```