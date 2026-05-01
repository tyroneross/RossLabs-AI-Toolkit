# GitHub Actions templates — TestFlight via tag push

Three reusable workflows that upload an iOS or macOS app to TestFlight from CI when a `testflight-*` tag is pushed. Builds happen in a clean macOS runner; the laptop never holds signing material at deploy time.

## Files

| File | Use it for |
|---|---|
| `ios-testflight.yml` | iOS-only apps (most projects) |
| `macos-testflight.yml` | macOS-only apps (e.g. Secrets Vault) |
| `dual-platform.yml` | Apps that ship both iOS and macOS from one repo (FloDoro) — one tag, two parallel uploads |

## What you need before copy-pasting

### 1. Repo secrets (GitHub → Settings → Secrets and variables → Actions)

| Secret | Source | Notes |
|---|---|---|
| `ASC_API_KEY_ID` | App Store Connect → Users and Access → Integrations → App Store Connect API | The 10-char key ID, e.g. `NTNAA84KU6` |
| `ASC_API_ISSUER_ID` | Same screen — top of the API Keys section | UUID |
| `ASC_API_KEY_BASE64` | Run `base64 -i AuthKey_<id>.p8` locally on your `.p8` file | The downloaded `.p8` from ASC, base64-encoded |
| `APPLE_TEAM_ID` | App Store Connect → Membership; or `Q6TB8685V9` for this user | 10-char string |

The reference for this user's ASC credentials lives at `~/.claude/projects/-Users-tyroneross/memory/reference_asc_credentials.md`. The `.p8` files are at `~/.private_keys/`. **Never commit a `.p8` file or paste raw key contents into a workflow file or commit message.**

### 2. Customize project-specific values inside the YAML

Each template has placeholder values that need to match the project:

- `App.xcodeproj` — replace with the actual `.xcodeproj` (or `.xcworkspace` with `-workspace` instead of `-project`)
- Scheme name (`"App"`, `"App-iOS"`, `"App-macOS"`) — find via `xcodebuild -list -project App.xcodeproj`
- `Xcode_16.app` path — bump if the runner image changes its default Xcode version

### 3. Copy into your project

```bash
mkdir -p .github/workflows
# Pick the right template:
cp ~/dev/git-folder/RossLabs-AI-Toolkit/templates/gh-actions/ios-testflight.yml \
   .github/workflows/ios-testflight.yml
git add .github/workflows/ios-testflight.yml
git commit -m "ci: add TestFlight workflow"
git push origin main
```

Then trigger it:

```bash
TAG="testflight-$(date +%Y%m%d-%H%M%S)"
git tag "$TAG"
git push origin "$TAG"
```

The workflow runs, archives, and uploads to TestFlight in ~10–15 minutes.

## Security model

These templates are deliberately conservative:

- **All `uses:` references are pinned to a commit SHA**, not a floating `@v4` tag. This prevents a compromised `actions/checkout` release tag from running arbitrary code in your CI. SHA pinning is the GitHub-recommended hardening for any workflow that handles secrets.
- **`permissions: contents: read`** at the workflow level. The `GITHUB_TOKEN` cannot write to the repo, push tags, or open PRs.
- **`persist-credentials: false`** on checkout. The token isn't kept in the runner's git config after the step.
- **No `pull_request_target` triggers.** These workflows only run on `push: tags: ['testflight-*']` from people who can already push to your repo.
- **Cleanup step** removes the decoded `.p8` from the runner at the end, even on failure.

### Secret rotation policy — 90 days

The App Store Connect API key (`ASC_API_KEY_BASE64`) is the highest-value secret in this setup. Rotate it every 90 days:

1. App Store Connect → Users and Access → Integrations → App Store Connect API → Generate new key (with the same TestFlight role).
2. Download the new `AuthKey_<new-id>.p8`.
3. Update three secrets in each repo using these workflows:
   - `ASC_API_KEY_ID` (new key ID)
   - `ASC_API_KEY_BASE64` (`base64 -i AuthKey_<new-id>.p8`)
   - `ASC_API_ISSUER_ID` (usually unchanged)
4. Trigger one TestFlight build per repo to confirm the rotation.
5. Revoke the old key in ASC.

Calendar reminder: set a recurring 90-day calendar event labeled "Rotate ASC API key (gh-actions)" so this doesn't drift.

### Why CI and not local

- Local laptops have signing certs in the keychain. Compromise of the laptop means TestFlight uploads from anywhere on your behalf.
- CI is ephemeral — the runner is destroyed after each job.
- The build that lands in TestFlight comes from a tagged commit on `main`, not from "whatever was on the laptop at the time."

## Updating the pinned action SHAs

When `actions/checkout` ships a new minor or patch version you trust, resolve the SHA before pinning:

```bash
curl -sL https://api.github.com/repos/actions/checkout/git/refs/tags/v4.2.3 \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['object']['sha'])"
```

Replace the SHA in each YAML file in this directory and commit. Floating `@v4` tags are easier but defeat the purpose of pinning.

## Reversibility

Per workflow file: delete the YAML from `.github/workflows/` and push. Repo secrets remain in GitHub Settings until you remove them manually.
