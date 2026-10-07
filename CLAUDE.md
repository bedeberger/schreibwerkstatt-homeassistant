# Agent instructions

Conventions that apply to every coding-agent session in this repository.

## `/release` is end-to-end

When the user invokes `/release`, do the whole flow from
`.claude/commands/release.md` (pre-checks, version bump, lint, tests,
release notes, commit, tag, **`git push` to `origin/main` and `origin/v<version>`**,
`gh release create`). Push is part of the workflow — never stop after the
local commit/tag.

The release is the artifact HACS shows under *Einstellungen → Updates*; a
local tag or a commit on `main` alone does nothing there. Verify the push
landed (`git ls-remote --tags origin v<version>`) before
`gh release create`.