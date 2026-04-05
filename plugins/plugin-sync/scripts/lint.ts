import fs from 'node:fs';
import path from 'node:path';
import type { SourcePlugin } from './scan.ts';
import { collapseHome } from './util.ts';

/**
 * Lint result for a single plugin.json path-field issue.
 */
export interface LintIssue {
  plugin: string;
  pluginJsonPath: string;
  field: string;
  rawValue: string;
  problem: 'parent-escape' | 'bare-path' | 'missing-target' | 'not-a-string';
  message: string;
}

/** Path fields in plugin.json that should resolve to files/dirs under the plugin root */
const PATH_FIELDS = ['hooks', 'skills', 'commands', 'agents'] as const;

/**
 * Lint each source plugin's plugin.json against the manifest reference
 * (plugin-dev:plugin-structure/references/manifest-reference.md).
 *
 * Rules enforced:
 *   1. Path fields (hooks, skills, commands, agents) must start with `./`
 *      or `./subdir` — bare paths like `hooks/hooks.json` are rejected by
 *      the loader.
 *   2. Path fields must not start with `../` — this escapes the plugin root
 *      and will silently fail to load.
 *   3. The target of each path field must exist on disk.
 *   4. mcpServers can be either an object (inline server definitions) or
 *      a string path — if a string, the same ./ rules apply.
 */
export function lintPlugins(plugins: SourcePlugin[]): LintIssue[] {
  const issues: LintIssue[] = [];

  for (const plugin of plugins) {
    const raw = plugin.raw;

    // Validate standard path fields
    for (const field of PATH_FIELDS) {
      const value = raw[field];
      if (value === undefined || value === null) continue;
      if (typeof value !== 'string') {
        issues.push({
          plugin: plugin.name,
          pluginJsonPath: plugin.pluginJsonPath,
          field,
          rawValue: JSON.stringify(value),
          problem: 'not-a-string',
          message: `${field} must be a string path, got ${typeof value}`,
        });
        continue;
      }
      checkPath(plugin, field, value, issues);
    }

    // mcpServers is special — can be object (inline) or string (path)
    const mcp = raw.mcpServers;
    if (typeof mcp === 'string') {
      checkPath(plugin, 'mcpServers', mcp, issues);
    }
  }

  return issues;
}

function checkPath(plugin: SourcePlugin, field: string, value: string, issues: LintIssue[]): void {
  // Rule 1: parent-dir escape
  if (value.startsWith('../')) {
    issues.push({
      plugin: plugin.name,
      pluginJsonPath: plugin.pluginJsonPath,
      field,
      rawValue: value,
      problem: 'parent-escape',
      message: `"${value}" escapes the plugin root with \`../\`. Paths must stay under the plugin root. Use "./${value.replace(/^\.\.\//, '')}" instead.`,
    });
    return;
  }

  // Rule 2: bare path without ./
  if (!value.startsWith('./') && !value.startsWith('/')) {
    issues.push({
      plugin: plugin.name,
      pluginJsonPath: plugin.pluginJsonPath,
      field,
      rawValue: value,
      problem: 'bare-path',
      message: `"${value}" is missing the required \`./\` prefix. Use "./${value}" instead.`,
    });
    return;
  }

  // Rule 3: target must exist
  // Resolve relative to the plugin root (dir containing .claude-plugin/)
  const resolved = path.resolve(plugin.sourceDir, value);
  if (!fs.existsSync(resolved)) {
    issues.push({
      plugin: plugin.name,
      pluginJsonPath: plugin.pluginJsonPath,
      field,
      rawValue: value,
      problem: 'missing-target',
      message: `"${value}" resolves to ${collapseHome(resolved)}, which does not exist.`,
    });
  }
}
