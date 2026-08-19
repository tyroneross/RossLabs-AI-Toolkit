---
name: publish-packages
description: |
  How to publish a public npm package to GitHub Packages for any project under the @tyroneross scope — Claude Code plugins, build-loop subsystems, prompt-builder, etc. Load whenever the user asks to "publish to GitHub Packages", "publish the plugin", "ship as an npm package", "make this installable", "release this to npm", or whenever bumping a package version that needs to ship. Covers single-package repos (build-loop pattern) and monorepo per-plugin publishing (RossLabs-AI-Toolkit pattern). Includes the GitHub Actions workflow template, the release ritual, and the verification checklist that catches the 403 / version-drift / scope-missing failures already seen in this account. Not for marketplace.json listing, version drift across repo surfaces, or add-marketplace failures — use `marketplace-maintenance`.
---

# Publish Packages — GitHub Packages, @tyroneross scope

Canonical reference for shipping a public npm package on GitHub Packages. Pattern proven on `@tyroneross/build-loop@0.12.16` (2026-05-26 release).

Two shapes:

| Shape | Example | When |
|---|---|---|
| **Single-package repo** | `tyroneross/build-loop` → `@tyroneross/build-loop` | One repo, one publishable artifact. Tag `v<X.Y.Z>` triggers publish. |
| **Monorepo per-plugin** | `tyroneross/RossLabs-AI-Toolkit` → `@tyroneross/<plugin-name>` per plugin | One repo ships multiple packages. Tag `<plugin>-v<X.Y.Z>` triggers per-plugin publish. |

## Pilot status (toolkit)

- **prompt-builder** — designated next pilot for the monorepo pattern. Currently a Claude Code plugin shape (commands/, skills/, evals/) with no `package.json`. Wiring deferred until explicitly requested.
- All other toolkit plugins: not yet packaged.

When the user says "wire <plugin> to publish", follow the monorepo section below.

## Prerequisites

**One-time per workstation:**
1. `gh auth status` should show scopes including `write:packages` and `read:packages`. If not:
   ```
   gh auth refresh -s read:packages,write:packages
   ```
   (Interactive — opens browser. Read-only consumers only need `read:packages`.)

**One-time per package:**
1. `package.json` exists with the correct shape (see template below). For pure plugin shapes that don't currently have one, add it.
2. Repo has a `.github/workflows/publish-npm.yml` (or per-plugin variant for monorepos).

## `package.json` shape — required fields

```json
{
  "name": "@tyroneross/<package-name>",
  "version": "<X.Y.Z>",
  "description": "<one-line>",
  "license": "Apache-2.0",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/tyroneross/<repo-name>.git"
  },
  "publishConfig": {
    "registry": "https://npm.pkg.github.com",
    "access": "public"
  }
}
```

Why each one:
- **Scoped name** (`@tyroneross/…`) — GitHub Packages requires scope to match the owner.
- **`repository.url`** in `git+https://` form — registry warnings disappear; consumers can `npm bug`.
- **`publishConfig.registry`** — pins publish target so a stray `~/.npmrc` can't redirect to npmjs.org.
- **`access: public`** — without this, GitHub Packages defaults to inheriting repo visibility, which fails silently for org packages on free plans.

For monorepos, **also** add `"private": false` explicitly to override any root manifest defaults.

## Workflow template — single-package repo

Canonical reference: [`tyroneross/build-loop` publish-npm.yml](https://github.com/tyroneross/build-loop/blob/main/.github/workflows/publish-npm.yml).

`.github/workflows/publish-npm.yml`:

```yaml
# SPDX-FileCopyrightText: 2025-2026 Tyrone Ross, Jr <46267523+tyroneross@users.noreply.github.com>
# SPDX-License-Identifier: Apache-2.0
name: Publish @tyroneross/<package-name> to GitHub Packages

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Run 'npm publish --dry-run' instead of publishing"
        required: false
        default: "false"

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://npm.pkg.github.com"
          scope: "@tyroneross"
          always-auth: true

      - name: Verify tag matches package.json version
        if: github.event_name == 'release'
        run: |
          PKG_VERSION=$(node -p "require('./package.json').version")
          TAG="${GITHUB_REF_NAME#v}"
          if [ "$PKG_VERSION" != "$TAG" ]; then
            echo "::error::package.json version ($PKG_VERSION) does not match release tag ($TAG)"
            exit 1
          fi

      - run: npm ci
      - run: npm run build  # omit if no build step

      - name: Publish (dry-run)
        if: github.event_name == 'workflow_dispatch' && github.event.inputs.dry_run == 'true'
        env:
          NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npm publish --dry-run

      - name: Publish
        if: github.event_name == 'release' || (github.event_name == 'workflow_dispatch' && github.event.inputs.dry_run != 'true')
        env:
          NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npm publish
```

Why each block:
- **`release: [published]`** — release creation is the trigger, not tag push. Lets you draft + edit release notes before shipping.
- **`workflow_dispatch` + `dry_run`** — manual smoke-test path. Run before the real release to surface auth/build issues without burning a version number.
- **Tag-vs-version guard** — catches the most common failure mode (forgot to bump `package.json` before tagging). Aborts the run cleanly before `npm publish`.
- **`GITHUB_TOKEN`** — no PAT needed. The default token has the right scope when `permissions.packages: write` is declared.

## Workflow template — monorepo per-plugin (RossLabs-AI-Toolkit)

For repos with many plugins, one workflow per plugin, filtered by tag prefix.

`.github/workflows/publish-<plugin>.yml`:

```yaml
name: Publish @tyroneross/<plugin> to GitHub Packages

on:
  push:
    tags:
      - "<plugin>-v*"          # e.g. prompt-builder-v1.2.3
  workflow_dispatch:
    inputs:
      dry_run:
        required: false
        default: "false"

permissions:
  contents: read
  packages: write

jobs:
  publish:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: plugins/<plugin>
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://npm.pkg.github.com"
          scope: "@tyroneross"
          always-auth: true

      - name: Verify tag matches package.json version
        if: github.event_name == 'push'
        run: |
          PKG_VERSION=$(node -p "require('./package.json').version")
          # Strip "<plugin>-v" prefix from tag (e.g. prompt-builder-v1.2.3 -> 1.2.3)
          TAG="${GITHUB_REF_NAME#<plugin>-v}"
          if [ "$PKG_VERSION" != "$TAG" ]; then
            echo "::error::version drift: pkg=$PKG_VERSION tag=$TAG"
            exit 1
          fi

      - run: npm ci
      - run: npm run build || true   # only if the plugin has a build step

      - name: Publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if [ "${{ github.event.inputs.dry_run }}" = "true" ]; then
            npm publish --dry-run
          else
            npm publish
          fi
```

Why per-plugin instead of one matrix workflow:
- Tag scoping is unambiguous (`prompt-builder-v*` can't accidentally publish `build-loop`).
- A broken plugin doesn't block sibling releases.
- Each plugin's CI minutes are billed against its own workflow — easier to read in the Actions UI.

## Release ritual

Single-package repo:

```bash
# 1. Bump version (in package.json + any siblings — plugin.json, pyproject.toml)
npm version <patch|minor|major> --no-git-tag-version
# Edit other manifests by hand to match.

# 2. Commit
git add package.json <other-manifests>
git commit -m "chore(release): prep vX.Y.Z"

# 3. Tag and push
git tag vX.Y.Z
git push origin main vX.Y.Z

# 4. Create the GitHub Release (triggers the workflow)
gh release create vX.Y.Z -F docs/releases/vX.Y.Z.md \
  --title "vX.Y.Z — <headline>"
```

Monorepo per-plugin (from repo root):

```bash
cd plugins/<plugin>
npm version <bump> --no-git-tag-version
cd ../..
git add plugins/<plugin>/package.json
git commit -m "chore(<plugin>): release vX.Y.Z"
git tag <plugin>-vX.Y.Z
git push origin main <plugin>-vX.Y.Z
```

Note: monorepo workflow above fires on tag push directly — no `gh release create` required. Add one anyway if you want changelog visibility on the repo's Releases page.

## Verification

Two paths. **Prefer the CI smoke test** — no PAT shuffling, runs on every future publish, catches regressions.

### Primary: CI smoke-test workflow (recommended)

Add a sibling `.github/workflows/verify-install.yml` that chains after the publish workflow. Uses the auto-provisioned `GITHUB_TOKEN` (which gets `packages:read` for free when declared in `permissions:`), so consumers/maintainers never need to mint a PAT just to verify.

Reference impl: [`tyroneross/build-loop` verify-install.yml](https://github.com/tyroneross/build-loop/blob/main/.github/workflows/verify-install.yml).

```yaml
# SPDX-FileCopyrightText: 2025-2026 Tyrone Ross, Jr <46267523+tyroneross@users.noreply.github.com>
# SPDX-License-Identifier: Apache-2.0
name: Verify @tyroneross/<package> install

on:
  workflow_run:
    workflows: ["Publish @tyroneross/<package> to GitHub Packages"]
    types: [completed]
  workflow_dispatch:
    inputs:
      version:
        description: "Version to verify (omit to use current package.json)"
        required: false
        default: ""

permissions:
  contents: read
  packages: read

jobs:
  verify:
    runs-on: ubuntu-latest
    if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'
    steps:
      - uses: actions/checkout@v4

      - name: Resolve version
        id: ver
        run: |
          if [ -n "${{ inputs.version }}" ]; then
            V="${{ inputs.version }}"
          else
            V=$(node -p "require('./package.json').version")
          fi
          echo "version=$V" >> "$GITHUB_OUTPUT"

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://npm.pkg.github.com"
          scope: "@tyroneross"
          always-auth: true

      # GH Packages can lag the publish API by 30-60s when chained
      - name: Wait for propagation
        if: github.event_name == 'workflow_run'
        run: sleep 45

      - name: Sandbox install
        env:
          NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          mkdir -p /tmp/verify && cd /tmp/verify
          npm init -y >/dev/null
          npm install "@tyroneross/<package>@${{ steps.ver.outputs.version }}"

          # Read manifest via jq — require() fails when the package's
          # `exports` field doesn't expose ./package.json.
          INSTALLED=$(jq -r .version node_modules/@tyroneross/<package>/package.json)
          [ "$INSTALLED" = "${{ steps.ver.outputs.version }}" ] || {
            echo "::error::version drift: installed=$INSTALLED requested=${{ steps.ver.outputs.version }}"
            exit 1
          }

          FILE_COUNT=$(find node_modules/@tyroneross/<package> -type f | wc -l | tr -d ' ')
          [ "$FILE_COUNT" -ge 10 ] || {
            echo "::error::Suspiciously small install — only $FILE_COUNT files"
            exit 1
          }

          echo "::notice::Verified @tyroneross/<package>@$INSTALLED — $FILE_COUNT files installed"
```

Why this shape:
- **`workflow_run` chain** — auto-runs after every successful publish. No human in the loop.
- **`workflow_dispatch` + version input** — ad-hoc verification of any past version.
- **`jq` over `require()`** — packages with strict `exports` fields block `require('@scope/pkg/package.json')`. `jq` reads the file directly. Already preinstalled on ubuntu-latest.
- **File-count assertion** — guards against empty-tarball regressions (where publish succeeds but `.npmignore`/`files:` accidentally strip everything).
- **45s sleep on `workflow_run`** — GH Packages registry index lags the publish API. Skip when manually triggered.

Trigger manually via:
```bash
gh workflow run verify-install.yml -f version=<X.Y.Z>
gh run watch <run-id> --exit-status
```

### Fallback: local sandbox install

When you want to reproduce a consumer issue locally (or you don't have the CI workflow yet):

```bash
# Requires read:packages on your gh token
gh auth refresh -s read:packages   # one-time, if not already set

TMP=$(mktemp -d) && cd "$TMP"
echo "@tyroneross:registry=https://npm.pkg.github.com" > .npmrc
echo "//npm.pkg.github.com/:_authToken=$(gh auth token)" >> .npmrc
npm init -y >/dev/null
npm install @tyroneross/<package>@<version>
jq -r .version node_modules/@tyroneross/<package>/package.json
```

### Other checks

```bash
# Workflow status
gh run list --workflow=publish-npm.yml --limit 3
gh run list --workflow=verify-install.yml --limit 3

# Package metadata (needs read:packages on token)
gh api "users/tyroneross/packages?package_type=npm" \
  --jq '.[] | {name, visibility, html_url}'
```

## Common failures (already seen in this account)

| Symptom | Cause | Fix |
|---|---|---|
| `403` when consumer runs `npm install` | Consumer's `gh` token / PAT missing `read:packages` | `gh auth refresh -s read:packages` |
| `403` on `gh api .../packages` | Same — token scope | Same fix |
| Workflow fails at `npm publish` with `401 Unauthorized` | `permissions.packages` not set in workflow, or scoped `registry-url` missing in `setup-node` | Add both. The `setup-node` registry-url writes the `.npmrc` line that authenticates the publish |
| Workflow publishes but version is wrong | Tag pushed without bumping `package.json` | The version-drift guard catches this in `if: github.event_name == 'release'` block. Re-tag after fixing |
| Local install pulls from npmjs.org instead of GH Packages | Missing `.npmrc` line, or scope-to-registry binding not set in user's global config | Per-project `.npmrc` with `@tyroneross:registry=https://npm.pkg.github.com` overrides global |
| Package shows as private on GH despite `access: public` | `publishConfig.access` not set, or repo is private (inherits) | Add `access: public`, ensure repo is public |
| `npm notice` warnings about `repository.url` | URL not in `git+https://` form | Change to `git+https://github.com/<owner>/<repo>.git` |
| `ERR_PACKAGE_PATH_NOT_EXPORTED` when verifying via `require('@scope/pkg/package.json')` | Package's `exports` field doesn't whitelist `./package.json` | Read manifest via `jq -r .version node_modules/@scope/pkg/package.json` instead. Don't add to `exports` just for verification — let the verify script adapt |
| `Node.js 20 actions are deprecated` warning in workflow logs | `actions/checkout@v4` + `actions/setup-node@v4` run on Node 20; forced to Node 24 starting 2026-06-02 | Bump to `@v5` when available, or set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to opt in early. Non-blocking until the forced switch |

## Pre-flight checklist

Before tagging:

- [ ] `package.json` version bumped and matches the tag you're about to push
- [ ] Sibling manifests (`plugin.json`, `pyproject.toml`, etc.) bumped to match
- [ ] `publishConfig` block present with `registry` + `access: public`
- [ ] `repository.url` in `git+https://` form
- [ ] If repo has a build step, `npm run build` succeeds locally
- [ ] `npm publish --dry-run` succeeds locally (catches `.npmignore` / `files:` mistakes)
- [ ] Release notes file exists if using `gh release create -F`

## Anti-patterns

- **Don't `--amend` to re-tag.** Bump version, new commit, new tag. Amending shifts SHAs and confuses consumers who already pulled.
- **Don't publish from `main` without a tag.** The workflow gates on release/tag events. A manual `workflow_dispatch` without bumping version overwrites whatever's at `package.json` — silently.
- **Don't paste a PAT into the workflow.** `GITHUB_TOKEN` + correct `permissions:` block is enough. PATs leak.
- **Don't rely on `latest` tag working immediately.** GitHub Packages doesn't auto-update dist-tags the same way npmjs does. Pin a version when verifying.

## Related

- `marketplace-maintenance` skill — for the Claude Code marketplace half of plugin distribution. They're independent: a plugin can be on the marketplace without being on npm, and vice versa.
- `attribution-standard` skill — for the SPDX/copyright headers required on the workflow file.
