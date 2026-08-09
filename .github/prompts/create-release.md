---
name: create-release
description: Create and publish a patch, minor, or major release
---

# Create a Release

Ask the user exactly one question before doing anything else:

> Which release type should I create: patch, minor, or major?

Pause for the answer. Accept only `patch`, `minor`, or `major`
(case-insensitive); do not infer the release type from the repository state.
After receiving a valid answer, take ownership of the remaining release work.

## Prepare the release

Read `AGENTS.md`, `.github/workflows/release.yml`, `pyproject.toml`, and the
latest entries in `CHANGELOG.md`. Use the dispatchable trusted-publishing
workflow rather than uploading distributions from the developer's machine.

1. Verify `gh` authentication, fetch and prune `origin`, and inspect the working
   tree. Preserve unrelated local changes. If necessary, use a clean worktree.
2. Start from the latest `origin/main`. Confirm that the version in
   `pyproject.toml`, the latest GitHub release tag, and the latest PyPI release
   describe the expected current stable version.
3. Use the current `uv` CLI to preview the requested semantic version bump and
   capture the computed version:

   ```bash
   uv version --bump <patch|minor|major> --dry-run
   ```
4. Create a `release-vx.y.z` branch for the computed version.
5. Apply the bump with `uv version --bump <patch|minor|major>`. Keep the project
   entry in `uv.lock` synchronized; never edit the lockfile by hand.
6. Review commits and merged pull requests since the latest release. Add a dated
   version section at the top of `CHANGELOG.md` using its existing Keep a
   Changelog categories and style. Include every user-facing change and do not
   invent entries.
7. Prepare a release-notes file whose Markdown content exactly matches the new
   changelog entry, excluding only the changelog heading when necessary for the
   GitHub release title.
8. Check open code-scanning alerts. Fix legitimate findings before release;
   dismiss an alert only when repository evidence proves the documented
   dismissal reason.

## Validate and merge the release pull request

Run the complete local gate and inspect the built wheel and source distribution:

```bash
make check-package
uv build
git diff --check
```

Confirm that artifact filenames contain the new version, then remove untracked
build artifacts. Inspect the final diff and commit only the intended version,
lockfile, and changelog changes. Push the release branch and open a
ready-for-review pull request against `main` whose title identifies the version
and whose body lists the release notes and validation.

Monitor the pull request until every required check passes and no unresolved
review threads remain. Address actionable feedback, push fixes, and rerun the
relevant gates. When the pull request is mergeable and green, squash-merge it.
Verify that `origin/main` contains the release commit before publishing.

## Publish and verify

Dispatch the trusted-publishing workflow from the merged `main` branch:

```bash
gh workflow run release.yml --ref main
```

Find the resulting run, watch it to completion, and inspect logs if it fails.
Do not retry blindly after a tag or package version may already have been
published.

After a successful run:

- verify the exact version exists on PyPI by installing it in an isolated `uv`
  environment and checking its installed metadata;
- verify the GitHub release tag and target commit;
- replace generated GitHub release notes with the prepared notes so that they
  match `CHANGELOG.md` exactly; and
- re-open the release to confirm its title, tag, body, and assets.

Report the pull request, merge commit, workflow run, GitHub release, PyPI
version, and all validations. Do not claim publication succeeded until both
GitHub and PyPI are verified.
