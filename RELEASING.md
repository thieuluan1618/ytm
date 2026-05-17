# Release Process

This document describes how to cut a new `ytm-cli` release.

## TL;DR

```bash
# 1. Make sure main is green and you're on it
git checkout main && git pull
uv run pytest tests/ -q
uv run ruff check ytm_cli/ tests/

# 2. Update CHANGELOG (move [Unreleased] → [X.Y.Z])
$EDITOR CHANGELOG.md

# 3. Bump version (auto-commits + tags)
uvx bump2version patch        # 0.7.2 → 0.7.3
# or: minor / major

# 4. Push commit + tag
git push origin main
git push origin --tags

# 5. Create GitHub release (triggers PyPI publish)
gh release create v$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2) \
  --title "v$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2)" \
  --notes-from-tag
```

## Detailed Steps

### 1. Pre-release checklist

- [ ] All targeted PRs merged into `main`
- [ ] `main` is checked out locally and up-to-date with `origin/main`
- [ ] Working tree is clean (`git status` shows no changes)
- [ ] Test suite passes: `uv run pytest tests/ -q`
- [ ] Lint passes: `uv run ruff check ytm_cli/ tests/`
- [ ] Smoke-test the CLI: `uv run ytm-cli search "test" -s 1 --verbose` (Ctrl-C after a few seconds)

### 2. Update CHANGELOG.md

Open [CHANGELOG.md](CHANGELOG.md) and:

1. Rename the `## [Unreleased]` heading to `## [X.Y.Z] - YYYY-MM-DD`
2. Add a fresh empty `## [Unreleased]` section above it for future work
3. Group entries under standard headings: `### Added`, `### Changed`, `### Removed`, `### Fixed`
4. Keep entries terse but specific — link to files with relative paths like `[migrate_config.py](migrate_config.py)`
5. If the previous release was broken, mark it with a `> ⚠️ **Broken release**` note pointing to the fixed version

**Don't bump the version manually** — `bump2version` will do it in the next step.

### 3. Bump the version

`bump2version` updates `pyproject.toml`, `ytm_cli/__init__.py`, `.bumpversion.cfg`, then **commits and tags automatically** (see `.bumpversion.cfg`):

```bash
uvx bump2version patch    # 0.7.2  → 0.7.3   (bug fixes)
uvx bump2version minor    # 0.7.x  → 0.8.0   (new features, backwards-compatible)
uvx bump2version major    # 0.x.y  → 1.0.0   (breaking changes)
```

Verify it worked:

```bash
git log -1 --oneline      # → "Bump version: 0.7.2 → 0.7.3"
git tag -l | tail -3      # → v0.7.3
```

### 4. Push commit + tag

```bash
git push origin main
git push origin --tags
```

CI (`lint.yml`, `test.yml`) will run on the pushed commit. Wait for green ✅ before continuing.

### 5. Create the GitHub release

The PyPI publish workflow (`.github/workflows/publish.yml`) triggers on `release: published`, so creating the GitHub release **automatically publishes to PyPI**.

```bash
VERSION=$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2)

gh release create "v${VERSION}" \
  --title "v${VERSION}" \
  --notes-from-tag        # uses the annotated tag message
```

Or for a richer release body, pass `--notes-file <path-to-extracted-changelog-section.md>`.

### 6. Verify the publish

- [ ] Watch the workflow: `gh run watch` (or visit Actions tab)
- [ ] Confirm on PyPI: <https://pypi.org/project/ytm-cli/>
- [ ] Smoke-test the installed version:
  ```bash
  uvx --refresh ytm-cli@${VERSION} --version
  ```

## Hotfix Process

If a release is broken (e.g. the v0.7.1 situation):

1. Fix the bug on `main`
2. **Add a `> ⚠️ **Broken release**` note to the broken version's CHANGELOG entry** pointing users at the fix
3. Bump **patch** version: `uvx bump2version patch`
4. Push + release as normal (steps 4–6 above)

Do **not** delete the broken tag/PyPI release — yanking on PyPI (`pip install --no-cache ytm-cli==X.Y.Z` then yank via the web UI) is preferred over deletion so existing lockfiles don't break.

## Version Numbering (SemVer)

- **Patch** (`0.7.2 → 0.7.3`) — bug fixes only, no API/behavior changes
- **Minor** (`0.7.x → 0.8.0`) — new features, backwards-compatible
- **Major** (`0.x.y → 1.0.0`) — breaking changes (CLI args removed, config format changes, etc.)

Pre-1.0 the project is allowed minor-level breaks if clearly documented.

## Files Touched on Every Release

| File | What changes |
|---|---|
| [pyproject.toml](pyproject.toml) | `version = "X.Y.Z"` |
| [ytm_cli/\_\_init\_\_.py](ytm_cli/__init__.py) | `__version__ = "X.Y.Z"` |
| [.bumpversion.cfg](.bumpversion.cfg) | `current_version = X.Y.Z` |
| [CHANGELOG.md](CHANGELOG.md) | New version section, dated entry |

`bump2version` handles the first three automatically per [.bumpversion.cfg](.bumpversion.cfg). You handle CHANGELOG manually.
