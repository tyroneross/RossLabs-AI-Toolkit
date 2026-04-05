import fs from 'node:fs';
import path from 'node:path';
import type { SourcePlugin } from './scan.ts';
import { collapseHome } from './util.ts';

const HOOK_MARKER = '# installed-by: plugin-sync';

/**
 * The post-commit hook body written into each plugin repo's .git/hooks/ dir.
 * Runs plugin-sync fix when a commit touches .claude-plugin/plugin.json.
 * `.git/hooks/` is never tracked by git, so this stays machine-local.
 */
function hookBody(): string {
  return `#!/usr/bin/env bash
${HOOK_MARKER}
# Auto-runs plugin-sync fix when a version bump is detected in this repo.
# This hook lives in .git/hooks/ which is never tracked — safe to install per machine.

set -e

# Only fire if this commit touched .claude-plugin/plugin.json
if git diff-tree -r --name-only --no-commit-id HEAD 2>/dev/null | grep -q '^\\.claude-plugin/plugin\\.json$'; then
  if command -v plugin-sync >/dev/null 2>&1; then
    plugin-sync fix --quiet 2>&1 | sed 's/^/[plugin-sync] /' || true
  fi
fi

exit 0
`;
}

export interface HookResult {
  installed: string[];
  skipped: Array<{ plugin: string; reason: string }>;
  removed: string[];
}

/**
 * Install a post-commit hook in each source plugin's .git/hooks/ directory.
 * Refuses to overwrite an existing hook unless it carries the plugin-sync marker.
 */
export function installHooks(plugins: SourcePlugin[]): HookResult {
  const result: HookResult = { installed: [], skipped: [], removed: [] };

  for (const plugin of plugins) {
    const hooksDir = path.join(plugin.sourceDir, '.git', 'hooks');
    if (!fs.existsSync(hooksDir)) {
      result.skipped.push({ plugin: plugin.name, reason: 'not a git repo' });
      continue;
    }

    const hookPath = path.join(hooksDir, 'post-commit');
    if (fs.existsSync(hookPath)) {
      const existing = fs.readFileSync(hookPath, 'utf-8');
      if (!existing.includes(HOOK_MARKER)) {
        result.skipped.push({
          plugin: plugin.name,
          reason: `existing hook at ${collapseHome(hookPath)} (not written by plugin-sync; refusing to overwrite)`,
        });
        continue;
      }
    }

    fs.writeFileSync(hookPath, hookBody(), { mode: 0o755 });
    result.installed.push(plugin.name);
  }

  return result;
}

/**
 * Remove plugin-sync post-commit hooks from each plugin repo.
 * Only removes hooks that carry the plugin-sync marker.
 */
export function uninstallHooks(plugins: SourcePlugin[]): HookResult {
  const result: HookResult = { installed: [], skipped: [], removed: [] };

  for (const plugin of plugins) {
    const hookPath = path.join(plugin.sourceDir, '.git', 'hooks', 'post-commit');
    if (!fs.existsSync(hookPath)) {
      continue;
    }
    const existing = fs.readFileSync(hookPath, 'utf-8');
    if (!existing.includes(HOOK_MARKER)) {
      result.skipped.push({
        plugin: plugin.name,
        reason: `hook not written by plugin-sync — left alone`,
      });
      continue;
    }
    fs.unlinkSync(hookPath);
    result.removed.push(plugin.name);
  }

  return result;
}
