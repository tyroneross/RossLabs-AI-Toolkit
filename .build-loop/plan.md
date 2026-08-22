# Plan: mirror-to-main rule + build-loop 0.27.0 deploy + auto-sync

## Goal
Deploy build-loop 0.27.0 to RossLabs-AI-Toolkit and establish a durable rule that every plugin mirror under `plugins/` resolves to a working tree on `main`. Install the launchd auto-sync cron. Push to origin.

## Scoring criteria
1. `plugins/build-loop` symlink target reports `branch == main` and `plugin.json.version == 0.27.0`.
2. Three distribution surfaces all read build-loop @ 0.27.0: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `README.md`.
3. New mirror-on-main check exists in `scripts/marketplace-sync.py`, exits non-zero when ANY plugin mirror is off-main, has a fix command in stderr.
4. Test extension in `tests/test_marketplace_sync.py` covers the new check (pure-function tests, no live tree state).
5. launchd plist `~/Library/LaunchAgents/ai.rosslabs.marketplace-sync.plist` exists and is loaded.
6. Pushed to `origin/main` (one commit, clean diff).

## Depends-on (reads-from)

- `plugins/build-loop/.claude-plugin/plugin.json` (after Chunk 1: resolves to `build-loop-main-merge/.claude-plugin/plugin.json`) — read by `marketplace-sync.py` to source the truth version. Status: **verified** (file exists at the new target, version field = 0.27.0).
- `.claude-plugin/marketplace.json` — read by `marketplace-sync.py --check` and `build_version_map`. Status: **verified** (exists at toolkit root, well-formed JSON).
- `.agents/plugins/marketplace.json` — read by `apply_manifest`. Status: **verified** (exists, well-formed).
- `README.md` — read by `apply_readme`; regex `README_ROW_RE` matches the build-loop row. Status: **verified** (row matches regex, version `0.24.2` will be replaced).
- `~/dev/git-folder/build-loop-main-merge/.git/HEAD` — read by the new `scan_mirror_branches` via `git -C <target> branch --show-current`. Status: **verified** (worktree exists, on main, HEAD=9703c21).
- `tests/test_marketplace_sync.py` — read by `python3 -m pytest` to discover existing test classes; new class is appended. Status: **verified** (file exists, importable via `importlib.util`).
- `~/Library/LaunchAgents/` — read by `install_cron` to write the plist. Status: **verified** (directory exists or `mkdir -p` will create it; `install_cron` already handles both).
- `subprocess` calls to `git -C <target> branch --show-current` — Status: **verified** (git CLI present; symlinks resolve into git worktrees that respond to `-C`).

## Discovered state (Phase 1)

Audit of all 17 mirrors:
- 16 mirrors: already on `main`, HEAD == origin/main.
- 1 mirror (`build-loop`): on `codex/memory-graphstore-adapter` @ 0.26.0. Off-main.

build-loop has a sibling worktree `~/dev/git-folder/build-loop-main-merge` already checked out on `main` @ `9703c21` with `plugin.json.version == 0.27.0`. Has 5 local commits ahead of origin/main; origin/main is at `8f09733` (also 0.27.0). The local branch and origin/main have diverged but both report version 0.27.0 — the divergence is outside this run's scope.

The codex/memory-graphstore-adapter worktree at `~/dev/git-folder/build-loop` is potentially shared with a live peer; we MUST NOT touch its checked-out branch.

## Approach Lenses

**Clean-sheet best:** every plugin source repo would maintain a dedicated `main-tracking` worktree the marketplace symlinks point to; mirror targets are never the "default checkout" used for development. Each source repo's primary directory can be on any working branch without disrupting the marketplace mirror.

**Current-constraints:** the build-loop project already has a `build-loop-main-merge` worktree on main. Re-pointing the build-loop mirror to it is one-line and reversible. We don't need to introduce a new convention or migrate other plugins — every other plugin's "primary" directory already tracks main (because their source repos aren't multi-worktree). The rule reduces to: "mirror target must resolve to a git tree on `main`." Detection is `git -C <target> branch --show-current == "main"`. No new infrastructure.

**Constraint delta:** zero. The constraint-aware path here IS the clean-sheet ideal at the marketplace level.

**Recommendation:** current-constraints path.

## Pay-it-forward gate

This work changes a contract (the marketplace symlink invariant). Path B (typed-contract extension): the invariant is now enforced by `scripts/marketplace-sync.py --check` (which all surfaces already consult via the daily cron). No new surface; existing check mode gets a new rule. Foreclosed-futures list: none — the rule is generalizable across plugins and toolkits.

## Chunks

### Chunk 1 — re-point build-loop mirror to main worktree
**Owns:** `plugins/build-loop` (symlink target)
**Does not own:** the build-loop repo itself, the codex worktree
**Interface contract:** after this chunk, `readlink plugins/build-loop` resolves to a directory whose `git branch --show-current == main` and whose `.claude-plugin/plugin.json` has `version == 0.27.0`.
**Integration checkpoint:** `python3 -c "import json,pathlib; p=pathlib.Path('plugins/build-loop/.claude-plugin/plugin.json'); print(json.loads(p.read_text())['version'])"` prints `0.27.0`.

Steps:
1. `rm plugins/build-loop` (it's a symlink only — removes the link, not the target).
2. `ln -s /Users/tyroneross/dev/git-folder/build-loop-main-merge plugins/build-loop`.
3. Verify with `readlink` + `git -C plugins/build-loop branch --show-current` + version read.

Risk: low. Symlink swap, fully reversible (`ln -s ~/dev/git-folder/build-loop plugins/build-loop`).

`parallel_batch:` — sequential with Chunk 2/3 (Chunk 2 depends on this being done first to read the right version).

### Chunk 2 — extend marketplace-sync.py with mirror-on-main check
**Owns:** `scripts/marketplace-sync.py` (new functions + --check integration), `tests/test_marketplace_sync.py` (new test class).
**Does not own:** existing logic, README, marketplace JSONs.
**Interface contract:**
- New pure function `scan_mirror_branches(plugins_dir: Path) -> list[dict]` returns one record per symlink/dir under `plugins/`: `{name, target_path, branch, on_main, error}`.
- New filter `find_off_main_mirrors(records: list[dict]) -> list[dict]` returns only `on_main is False` entries.
- `--check` mode prints a section "Mirror branch hygiene" before the catalog section; on any off-main mirror, the section prints the name + current branch + fix command (`ln -s <suggested-main-target> plugins/<name>`) and contributes to the exit-3 drift count.
- `--check-hosts` (standalone) ALSO prints the section (consistent with package.json drift placement).

**Integration checkpoint:** `python3 -m pytest tests/test_marketplace_sync.py -v` passes; `python3 scripts/marketplace-sync.py --check` returns 2 (clean) after Chunk 1 lands.

Tests added:
- `test_scan_returns_list` — shape.
- `test_each_record_has_required_keys` — schema.
- `test_currently_all_mirrors_on_main` — live tree assertion (will fail before Chunk 1 lands; will pass after; that's the regression catch).
- `test_synthetic_off_main_detected` — feed synthetic records into `find_off_main_mirrors`, assert filter.
- `test_synthetic_all_on_main` — assert empty filter.
- `test_non_symlink_dir_handled` — a plain directory under plugins/ (rare; .claude-code-debugger leftover) must not crash.
- `test_non_git_target_handled` — symlink to non-repo must record `error` field, not crash.

Risk: medium. New pure functions + one integration into `check_all_surfaces`. All logic isolated, all paths covered by tests.

`parallel_batch:` — runs after Chunk 1 (so the live-tree test passes).

### Chunk 3 — reconcile distribution surfaces to 0.27.0
**Owns:** `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `README.md` (build-loop row only).
**Does not own:** any other plugin's version, any code.
**Interface contract:** `python3 scripts/marketplace-sync.py --all --source local --write` is the sole writer. Diff lands build-loop @ 0.27.0 in all three surfaces; no other plugin moves.

**Integration checkpoint:** `python3 scripts/marketplace-sync.py --check` returns 2 (clean — all surfaces synced).

Steps:
1. `python3 scripts/marketplace-sync.py --all --source local --write` (offline-safe; reads from `plugins/build-loop/.claude-plugin/plugin.json` which now resolves to the main worktree).
2. Capture stdout for the report.

Risk: low. Sync script is well-tested, --source local bypasses network.

`parallel_batch:` — runs after Chunks 1 + 2 land (so the mirror reflects 0.27.0 and tests pass).

### Chunk 4 — install launchd auto-sync cron
**Owns:** `~/Library/LaunchAgents/ai.rosslabs.marketplace-sync.plist`.
**Does not own:** anything in repo.
**Interface contract:** `launchctl list | grep ai.rosslabs.marketplace-sync` returns the job.
**Integration checkpoint:** plist file exists; `launchctl list` shows label.

Step: `python3 scripts/marketplace-sync.py --install-cron`.

Risk: low. Idempotent (script unloads existing job before reloading).

`parallel_batch:` — independent of other chunks; can run any time after Chunk 1.

### Chunk 5 — commit + push
**Owns:** git history of `~/dev/git-folder/RossLabs-AI-Toolkit`.
**Integration checkpoint:** `git push origin main` succeeds; `git status` shows clean tree.

One commit message:
```
feat(marketplace): build-loop 0.27.0 + mirror-on-main invariant + auto-sync cron

- Re-point plugins/build-loop at build-loop-main-merge (on main @ 0.27.0)
- Add mirror-branch hygiene check to marketplace-sync.py --check
- Sync .claude-plugin/marketplace.json, .agents/plugins/marketplace.json,
  README.md to build-loop 0.27.0
- Install launchd daily drift check (ai.rosslabs.marketplace-sync)
```

`parallel_batch:` — final step, sequential.

## Verification (final, before report)

1. `readlink plugins/build-loop` → `/Users/tyroneross/dev/git-folder/build-loop-main-merge`
2. `git -C plugins/build-loop branch --show-current` → `main`
3. `python3 -c "import json,pathlib; print(json.loads(pathlib.Path('plugins/build-loop/.claude-plugin/plugin.json').read_text())['version'])"` → `0.27.0`
4. `python3 scripts/marketplace-sync.py --check` → exit 2 (clean)
5. `python3 -m pytest tests/test_marketplace_sync.py -v` → all green
6. `ls ~/Library/LaunchAgents/ai.rosslabs.marketplace-sync.plist` → exists
7. `git log -1 --oneline origin/main` → matches local HEAD after push

## Risks + rollback

- **Risk: build-loop-main-merge worktree gets re-checked-out off main.** Mitigation: the new --check rule catches it; the cron reports daily.
- **Risk: cron interferes during active development.** Mitigation: --check is read-only, exits without modifying anything. Logs to ~/Library/Logs/.
- **Rollback:** `ln -sf /Users/tyroneross/dev/git-folder/build-loop plugins/build-loop` restores prior symlink; `git revert HEAD` undoes the commit; `launchctl unload ~/Library/LaunchAgents/ai.rosslabs.marketplace-sync.plist && rm ~/Library/LaunchAgents/ai.rosslabs.marketplace-sync.plist` removes the cron.

## DECISION (auto-resolved, recorded for memory)

The mirror-to-main mechanism is **a check in marketplace-sync.py + the existing convention that mirror symlinks target main-tracking working trees**, NOT a git hook in each source repo (which would require touching 17 separate repos). The toolkit owns its own invariant; source repos remain free to use any branching strategy in their primary checkout. user_impact: minor (architectural choice between equivalent paths; the script-side approach is durable and locally enforceable).
