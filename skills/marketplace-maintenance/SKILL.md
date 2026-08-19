---
name: marketplace-maintenance
description: |
  Operational lessons for maintaining a Claude Code plugin marketplace. Load whenever making changes to `.claude-plugin/marketplace.json`, bumping a plugin version that's listed in a marketplace, adding/removing plugins from a marketplace, or troubleshooting "add marketplace" failures. Prevents schema rejection, stale manifests, CDN-lag false negatives, and install-command drift. Not for the npm/GitHub Packages publish step itself — use `publish-packages`.
---

# Marketplace Maintenance

Operational knowledge for maintaining a Claude Code plugin marketplace. Reference whenever touching `.claude-plugin/marketplace.json` or documenting install commands.

Based on real incidents from the RossLabs-AI-Toolkit marketplace (2026-04-20 session).

## Required sync whenever a plugin change ships

A plugin version lives on **four** repo surfaces that drift independently. When any plugin bumps its version, changes description, or ships significant features, reconcile all four in lockstep:

1. **`.claude-plugin/marketplace.json`** — the entry's `version`, `description`, `keywords`. Drives Claude Code installs.
2. **`.agents/plugins/marketplace.json`** — the Codex / cross-agent mirror. Carries `version` only on the subset of entries that declare it (today: `build-loop`). Update existing version fields; do **not** inject `version` into entries that omit it by design. Every public plugin in `.claude-plugin/marketplace.json` that has a Codex-compatible repo surface should have a matching `.agents` entry.
3. **`README.md`** — Plugins table row + install-example block. Drives GitHub discovery.
4. **`plugins/README.md`** — Plugin index table. Drives repo-local plugin discovery and version audits.

Drift between these surfaces is the #1 symptom of a stale marketplace. The classic failure is three different versions for one plugin (README `0.12.10`, `.claude-plugin` `0.12.16`, external repo `0.13.5`). Don't hand-edit — run the reconciler:

```bash
# Source of truth = each plugin's EXTERNAL repo plugin.json (what install actually clones)
python3 scripts/marketplace-sync.py --all            # dry-run: show drift across repo surfaces
python3 scripts/marketplace-sync.py --all --write    # apply
```

`--all` resolves every plugin's true version from its external github repo via `gh api` (falling back to the local mirror only if gh/network is unavailable), then updates both manifests' `version` fields plus the README and plugin-index version cells in one pass. It does **not** touch curated descriptions or the install-command lists — those stay hand-authored, so re-check install-list completeness (all current plugins listed, deprecated ones excluded) manually after a plugin is added or retired.

## Codex marketplace support

Codex installs use the `.agents/plugins/marketplace.json` mirror. With Codex CLI 0.130.0, marketplace operations are marketplace-scoped:

```bash
codex plugin marketplace add tyroneross/RossLabs-AI-Toolkit --sparse .agents/plugins
codex plugin marketplace upgrade ross-labs-local
```

Do not document removed per-plugin commands such as `codex plugin list`, `codex plugin add`, or `codex plugin remove` as the current install path. For host drift checks, `scripts/marketplace-sync.py` reads `~/.codex/config.toml` plus `~/.codex/plugins/cache/`.

## Schema requirements (per Anthropic docs)

**Required top-level fields:**
- `name` — kebab-case, no spaces, no uppercase. Validator warns on mixed-case. `rosslabs-ai-toolkit` ✓, `RossLabs-AI-Toolkit` ✗.
- `owner` — object with `name` (required) and optional `email`.
- `plugins` — array of plugin entries.

**Optional top-level metadata:**
- `metadata.description` — brief marketplace description. **NOT `description` at top level** — that's a schema violation (schema accepts only `name`, `owner`, `plugins`, `metadata` at root).
- `metadata.version` — marketplace version (separate from plugin versions).
- `metadata.pluginRoot` — base directory for relative plugin sources.

**Do NOT include a `$schema` key at root** — Anthropic's `claude plugin validate` rejects it as an unrecognized root key, even though JSON Schema convention allows it.

**Each plugin entry requires:**
- `name` — kebab-case.
- `source` — string (relative path starting with `./`) OR object (`{ source: "github", repo: "owner/repo", ref?, sha? }` / `url` / `git-subdir` / `npm`).

**Each plugin entry optionally includes:** `version`, `description`, `author` (object), `homepage`, `repository`, `license`, `keywords` (array), `category`, `tags`, `strict` (boolean), plus component configs (`skills`, `commands`, `agents`, `hooks`, `mcpServers`).

## Validate before pushing

```bash
claude plugin validate <marketplace-dir>
```

Runs Anthropic's official validator. Catches:
- Unrecognized root keys (e.g. stray `$schema`, `description` at top level)
- Missing `owner` / `plugins` / per-plugin `name` / `source`
- Malformed JSON syntax
- Kebab-case violations (warning, not blocking)

Always run this before committing a change to a marketplace manifest.

## "Add marketplace" input format

The `/plugin marketplace add` dialog (and CLI `claude plugin marketplace add`) takes one of:

- GitHub shorthand: `owner/repo` (e.g. `tyroneross/RossLabs-AI-Toolkit`)
- GitHub shorthand with ref: `owner/repo@ref` (e.g. `acme/plugins@v2.0`)
- Full git URL: `https://gitlab.example.com/team/plugins.git` (`.git` suffix optional)
- Git URL with ref: `https://example.com/plugins.git#main`
- Direct `marketplace.json` URL: `https://example.com/marketplace.json`
- Local path: `./path/to/marketplace`

**Common mistake**: pasting a GitHub web URL like `https://github.com/owner/repo/tree/main`. Claude Code interprets any URL input as a raw git URL and appends `.git/` to the end → `https://github.com/owner/repo/tree/main.git/` → 404 "repository not found".

**Fix**: use the `owner/repo` shorthand, not the browser URL.

Always document this pitfall in the marketplace README.

## Verifying a push landed correctly

After committing to a public marketplace, verify via the GitHub API — NOT `raw.githubusercontent.com`. Raw CDN has a 30-60 second propagation lag and will return stale content.

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/contents/.claude-plugin/marketplace.json?ref=main" \
  | python3 -c "
import sys, json, base64
r = json.load(sys.stdin)
d = json.loads(base64.b64decode(r['content']))
print(f'commit sha: {r[\"sha\"][:8]}')
print(f'name: {d[\"name\"]}')
for p in d['plugins']:
    print(f'  {p[\"name\"]}: v{p.get(\"version\", \"?\")}')"
```

## Renaming a marketplace safely

If renaming the marketplace's `name` field (e.g. legacy mixed-case → kebab-case):

1. **Understand the blast radius first** — every user who installed plugins via `<plugin>@<old-name>` has those install records keyed by the old name. Their plugins stop working until they reinstall.
2. **Update in one commit**: `marketplace.json`, all READMEs (root + per-plugin + per-skill), any documentation mentioning `@<old-name>` in install commands.
3. **Do NOT change** the GitHub repository path (`owner/repo` in install commands like `claude plugin marketplace add owner/repo`). That's a different identifier — the repo path on GitHub is unchanged unless you rename the actual repo.
4. **Local state cleanup** — delete stale `~/.claude/plugins/marketplaces/<old-name>/` directory. Claude Code will re-clone under the new name on next `marketplace add`.
5. **Communicate the rename** in the commit message and README so existing users know to `marketplace remove <old-name>` + `marketplace add <new-path>` + reinstall.

## Common operational failures

| Symptom | Cause | Fix |
|---|---|---|
| "Failed to parse marketplace file" | Extra root key like `$schema` or `description` at top level | Remove unrecognized keys; put description under `metadata.description` |
| "Failed to clone" with weird `.git/` suffix | User pasted web URL in add dialog | Use `owner/repo` shorthand |
| Install command works on one machine, fails on another | Local `known_marketplaces.json` has stale entry pointing at wrong directory | Delete the stale entry + re-add fresh |
| Plugin version stale in marketplace but fresh in plugin.json | Forgot to propagate bump to marketplace.json | Sync rule above — always update both |
| Marketplace shows old content after push | Raw CDN lag | Verify via GitHub contents API instead |
| `claude plugin validate` rejects despite valid JSON | Anthropic's schema rejects unrecognized root keys (stricter than JSON Schema convention) | Remove any `$schema`, top-level `description`, etc. — only `name` / `owner` / `plugins` / `metadata` are accepted at root |

## When to use this skill

- **Every time** you bump a plugin version that's listed in any marketplace you maintain.
- **Before** committing any change to `.claude-plugin/marketplace.json`.
- **When** a user reports "can't add marketplace" or "can't install plugin".
- **When** a plugin is added to or removed from either marketplace manifest.
- **When** planning a marketplace rename.

## Related

- `plugin-sync` plugin at `~/Desktop/git-folder/RossLabs-AI-Toolkit/plugins/plugin-sync/` — automates propagation of plugin changes across marketplace + README + upstream patches.
- Anthropic docs: `https://code.claude.com/docs/en/plugin-marketplaces` — authoritative schema reference.
- Memory: `~/.claude/projects/-Users-tyroneross/memory/feedback_rosslabs_toolkit_sync.md` — session-specific lessons and verification commands.
