---
description: Check CI, bump version tag, build, and publish to PyPI
allowed-tools: Bash(gh run list:*), Bash(gh run view:*), Bash(git status:*), Bash(git add:*), Bash(git commit:*), Bash(git tag:*), Bash(git describe:*), Bash(git log:*), Bash(git diff:*), Bash(git rev-list:*), Bash(git push:*), Bash(uv build:*), Bash(uv lock:*), Bash(uv run ruff:*), Bash(uv run pytest:*), Bash(uv version:*), Bash(uvx twine check:*), Bash(uv publish:*), Bash(fish -c 'set -lx UV_PUBLISH_TOKEN $UV_PUBLISH_TOKEN; uv publish:*), Bash(fish -c 'set -q UV_PUBLISH_TOKEN:*), Bash(curl -s https://pypi.org/pypi/deckoction-md/json:*), Bash(rm -rf dist:*), Bash(date:*)
---

## Context

- Latest CI runs on master: !`gh run list --branch master --limit 5 --json conclusion,status,name,headSha,databaseId`
- Current tags: !`git tag --sort=-version:refname | head -5`
- Current branch: !`git branch --show-current`
- Uncommitted changes: !`git status --short`

## Your task

You are publishing a new release of slides_md to PyPI (distribution name `deckoction-md`; the
import package is `slide_maker`). Follow these steps in order, stopping and reporting
clearly if any step fails.

### Step 1 — Verify CI is green on master

Parse the CI run list above. Find the most recent completed run for the `CI` workflow on master. If its conclusion is not `success`, **stop immediately** and tell the user which job failed and what the run URL is (construct it as `https://github.com/julianholland/slides_md/actions/runs/<databaseId>`). Do not proceed until CI is green.

If CI is still in progress, tell the user and stop.

Also check that the run's `headSha` is the current `HEAD` (`git rev-list -1 HEAD`). If local master has commits CI hasn't seen, tell the user and ask whether to push and wait for CI first.

### Step 1b — Lint and lockfile

The project has no formatter configured (see CLAUDE.md), so only run the linter with auto-fix:

```bash
uv run ruff check . --fix
```

Also make sure the lockfile matches `pyproject.toml` (CI runs `uv sync --locked`, which fails on a stale lock):

```bash
uv lock --check || uv lock
```

If `uv lock` changed `uv.lock`, it is committed with the rest in Step 2.

If ruff reports unfixable errors after `--fix`, stop and report them — do not proceed with a broken codebase. If ruff modified any files, run `uv run pytest` to make sure nothing broke; the working-tree check in Step 2 will pick the changes up and commit them.

### Step 2 — Ensure a clean working tree

Check the `Uncommitted changes` output above (re-run `git status --short` to reflect any ruff changes). If any tracked files are modified or staged, **commit them before tagging**:

```bash
git add <files>
git commit -m "chore: pre-release cleanup"
```

The version comes from git tags (`hatch-vcs`, configured in `[tool.hatch.version]`). Building from a commit after the tag gives a `.postN` version (e.g. `0.3.0.post1` instead of `0.3.0`), so the tag must sit on the final, clean commit.

Only proceed to Step 3 once `git status --short` shows no modified tracked files. Untracked files (lines beginning with `??`) are fine and can be ignored.

### Step 3 — Determine the new version tag

The project uses `hatch-vcs` — the version is driven entirely by git tags (format: `vMAJOR.MINOR.PATCH`); there is no version number to edit in `pyproject.toml`.

If there are **no tags yet**, this is the first release: propose `v0.1.0` and ask the user to confirm (or pick another).

Otherwise show the user the current latest tag and ask them which version bump they want:
- **patch** (e.g. v0.2.0 → v0.2.1) — bug fixes only
- **minor** (e.g. v0.2.0 → v0.3.0) — new features (e.g. a new layout or frontmatter field), backwards-compatible
- **major** (e.g. v0.2.0 → v1.0.0) — breaking changes (e.g. a removed/renamed frontmatter field or CLI flag, changed output structure)

Wait for the user to confirm the new tag before proceeding.

### Step 3b — Update changelog, CLAUDE.md, and docs

Before tagging, ensure the release is documented.

**CHANGELOG.md:**
Read `CHANGELOG.md`. If an `## [Unreleased]` section exists, rename it to `## [<version without 'v'>] - <today's date>`. Get today's date with:
```bash
date +%Y-%m-%d
```
If there is no `[Unreleased]` section, warn the user and ask whether they want to add release notes before continuing.

**CLAUDE.md, README.md and docs/ — audit, don't just ask:**
Do not simply ask the user whether updates are needed. Make the judgement yourself from the actual changes since the last release:

1. Collect the changes since the previous tag (for the first release, use the root commit, `git rev-list --max-parents=0 HEAD`, in place of `<previous_tag>`):
   ```bash
   git log <previous_tag>..HEAD --oneline
   git diff <previous_tag>..HEAD --stat -- slide_maker/ docs/ examples/ README.md CLAUDE.md
   git diff <previous_tag>..HEAD -- slide_maker/
   ```
   Use the release's CHANGELOG entries as a guide to what changed, but verify against the diff: the changelog can be incomplete.
2. For each user-facing or architectural change (new layouts, new/changed frontmatter or `deck.yaml` fields, changed defaults, new CLI flags, new themes, new extras), check whether it is already documented:
   - **CLAUDE.md**: grep for the relevant function/module/field names and read the matching section.
   - **README.md**: the per-slide field reference and CLI flags.
   - **docs/**: grep `docs/` for the relevant names; check the page covering that subsystem (`docs/authoring-guide.md` for frontmatter fields/layouts, `docs/cli.md` for CLI flags, `docs/installation.md` for extras/install steps).
   - **`examples/demo/slides.md`**: CLAUDE.md requires it to exercise every layout/field — a new field or layout missing from it is a gap.
3. Report to the user, per change:
   - **Documented** → quote or cite (file:line) the section you think covers it.
   - **Not documented, or out of date** → draft the text you propose adding or replacing, and say where it would go.
4. Ask the user for feedback on the drafts, then apply only the approved edits (revised as the user asks). If everything is already documented, say so, show the evidence, and move on without editing.

**Commit all documentation changes:**
Once all edits are done, stage and commit only the files that were actually modified:
```bash
git add CHANGELOG.md CLAUDE.md README.md docs/ examples/
git commit -m "docs: update changelog and docs for <new_tag>"
```
If nothing changed, skip the commit. Pushing that commit to master triggers CI again — that's fine, the tag push below does not depend on it.

### Step 4 — Create and push the git tag

Once the user confirms the new version tag:

```bash
git tag -a <new_tag> -m "Release <new_tag>"
git push origin master
git push origin <new_tag>
```

Confirm the tag was pushed successfully.

### Step 5 — Build the package

Clean any previous build artifacts, then build the sdist and wheel with uv (the build backend is hatchling; no egg-info is produced):

```bash
rm -rf dist/
uv build
uvx twine check dist/*
```

Verify the built file names (`dist/deckoction_md-<version>.tar.gz` and `dist/deckoction_md-<version>-py3-none-any.whl` — note the underscore, PyPI normalizes it — also shown in the `uv build` output) carry exactly `<new_tag>` without the `v` and without any `.postN` or `.devN` suffix. If there is a suffix, **stop**: there are extra commits since the tag — go back to Step 2.

If `twine check` reports any errors, stop and report them. Do not upload a broken package.

### Step 6 — Upload to PyPI

`uv publish` uploads everything in `dist/`. It reads the PyPI API token from `UV_PUBLISH_TOKEN` and, unlike twine, does **not** read `~/.pypirc`. The user's token lives in their **fish** config (`~/.config/fish/config.fish`), which Claude's bash shell doesn't load — and bash's environment may hold a *different, stale* `UV_PUBLISH_TOKEN` that PyPI rejects with a 403. So run the upload through fish, re-exporting the variable for this one command (works whether config.fish uses `set -g` or `set -gx`):

```bash
fish -c 'set -lx UV_PUBLISH_TOKEN $UV_PUBLISH_TOKEN; uv publish --no-progress'
```

Never print, echo, log or otherwise display the token — not even partially, and not via `set -S`, `env`, `grep config.fish` or similar inspection commands (to check presence only, use `fish -c 'set -q UV_PUBLISH_TOKEN; and echo set'`) — and never write it to a file or into the chat. If there is no token (an authentication error such as "Missing credentials"), don't ask the user to paste it into the chat. Tell them to run it themselves:
- `! UV_PUBLISH_TOKEN=pypi-<token> uv publish`, **or**
- add `set -gx UV_PUBLISH_TOKEN pypi-...` to their fish config, then run `/publish` again.

A project-scoped token from another project (e.g. ALomancy's) cannot upload `deckoction-md`; for the first release the token must be account-wide (PyPI only allows project-scoped tokens once the project exists). If PyPI returns a 403 for that reason, tell the user.

If PyPI rejects the upload because the version already exists, the release was already published; go to Step 7.

After uploading, confirm the release is live:

```bash
curl -s https://pypi.org/pypi/deckoction-md/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"
```

(The PyPI JSON API can lag a minute or two behind the upload.)

### Step 7 — Confirm

Report the published version, the PyPI URL (`https://pypi.org/project/deckoction-md/<version>/`), and the git tag that was pushed.
