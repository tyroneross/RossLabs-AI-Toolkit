import fs from 'node:fs';
import path from 'node:path';
import { expandHome, readJsonOrNull } from './util.ts';

/** A plugin discovered in the filesystem via `.claude-plugin/plugin.json` */
export interface SourcePlugin {
  name: string;
  version: string;
  description: string;
  sourceDir: string;
  pluginJsonPath: string;
  codexPluginJsonPath: string | null;
  legacyCodexPluginJsonPath: string | null;
  readmePath: string | null;
  /** Raw plugin.json for passthrough when writing marketplace entries */
  raw: Record<string, unknown>;
}

export interface DuplicatePluginSource {
  name: string;
  sourceDirs: string[];
}

export class DuplicateSourcePluginError extends Error {
  constructor(public duplicates: DuplicatePluginSource[]) {
    super(
      duplicates
        .map((duplicate) => `${duplicate.name}: ${duplicate.sourceDirs.join(', ')}`)
        .join('\n')
    );
    this.name = 'DuplicateSourcePluginError';
  }
}

/** A manifest entry in a marketplace.json `plugins[]` array */
export interface MarketplacePlugin {
  name: string;
  version: string;
  source?: { source?: string; package?: string; version?: string };
  [key: string]: unknown;
}

export interface MarketplaceManifest {
  path: string;
  plugins: MarketplacePlugin[];
  raw: { plugins: MarketplacePlugin[]; [key: string]: unknown };
}

/** An entry in ~/.claude/plugins/installed_plugins.json */
export interface RegistryEntry {
  key: string;
  installPath: string;
  version: string;
  raw: Record<string, unknown>;
}

/**
 * Walk searchRoots and find every directory containing `.claude-plugin/plugin.json`.
 * Does not recurse into a plugin once found (prevents double-counting nested plugins).
 */
export function scanSourcePlugins(
  searchRoots: string[],
  exclude: string[],
  excludePaths: string[] = []
): SourcePlugin[] {
  const plugins: SourcePlugin[] = [];
  const excludeSet = new Set(exclude);
  const expandedExcludePaths = excludePaths.map((p) => path.resolve(expandHome(p)));

  for (const root of searchRoots) {
    const abs = expandHome(root);
    if (!fs.existsSync(abs)) continue;
    walk(abs, plugins, excludeSet, expandedExcludePaths);
  }

  // Sort for stable output
  plugins.sort((a, b) => a.name.localeCompare(b.name));
  throwOnDuplicatePluginNames(plugins);
  return plugins;
}

function walk(
  dir: string,
  plugins: SourcePlugin[],
  exclude: Set<string>,
  excludePaths: string[]
): void {
  if (isExcludedPath(dir, excludePaths)) return;

  const pluginJson = path.join(dir, '.claude-plugin', 'plugin.json');
  if (fs.existsSync(pluginJson)) {
    const raw = readJsonOrNull<Record<string, unknown>>(pluginJson);
    const codexPluginJson = path.join(dir, '.codex-plugin', 'plugin.json');
    const legacyCodexPluginJson = path.join(dir, '.Codex-plugin', 'plugin.json');
    const readmePath = path.join(dir, 'README.md');
    if (raw && typeof raw.name === 'string' && typeof raw.version === 'string') {
      plugins.push({
        name: raw.name,
        version: raw.version,
        description: typeof raw.description === 'string' ? raw.description : '',
        sourceDir: dir,
        pluginJsonPath: pluginJson,
        codexPluginJsonPath: fs.existsSync(codexPluginJson) ? codexPluginJson : null,
        legacyCodexPluginJsonPath: fs.existsSync(legacyCodexPluginJson)
          ? legacyCodexPluginJson
          : null,
        readmePath: fs.existsSync(readmePath) ? readmePath : null,
        raw,
      });
    }
    // Don't recurse into a plugin dir — prevents finding nested plugins twice
    return;
  }

  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (exclude.has(entry.name)) continue;
    // Skip hidden dirs except we still recurse into the top-level because
    // .claude-plugin/plugin.json is detected via the explicit path above.
    if (entry.name.startsWith('.')) continue;
    walk(path.join(dir, entry.name), plugins, exclude, excludePaths);
  }
}

function isExcludedPath(dir: string, excludePaths: string[]): boolean {
  const resolvedDir = path.resolve(dir);
  return excludePaths.some((excludedPath) => {
    if (resolvedDir === excludedPath) return true;
    return resolvedDir.startsWith(excludedPath + path.sep);
  });
}

function throwOnDuplicatePluginNames(plugins: SourcePlugin[]): void {
  const grouped = new Map<string, Set<string>>();

  for (const plugin of plugins) {
    const sourceDirs = grouped.get(plugin.name) ?? new Set<string>();
    sourceDirs.add(realSourceDir(plugin.sourceDir));
    grouped.set(plugin.name, sourceDirs);
  }

  const duplicates: DuplicatePluginSource[] = [];
  for (const [name, sourceDirs] of grouped) {
    if (sourceDirs.size < 2) continue;
    duplicates.push({
      name,
      sourceDirs: Array.from(sourceDirs).sort(),
    });
  }

  if (duplicates.length > 0) {
    duplicates.sort((a, b) => a.name.localeCompare(b.name));
    throw new DuplicateSourcePluginError(duplicates);
  }
}

function realSourceDir(sourceDir: string): string {
  try {
    return fs.realpathSync.native(sourceDir);
  } catch {
    return path.resolve(sourceDir);
  }
}

/** Read every marketplace.json listed in config.marketplaceManifests */
export function readMarketplaceManifests(manifestPaths: string[]): MarketplaceManifest[] {
  const manifests: MarketplaceManifest[] = [];
  for (const p of manifestPaths) {
    const abs = expandHome(p);
    const raw = readJsonOrNull<{ plugins?: MarketplacePlugin[]; [k: string]: unknown }>(abs);
    if (!raw || !Array.isArray(raw.plugins)) continue;
    manifests.push({
      path: abs,
      plugins: raw.plugins,
      raw: raw as { plugins: MarketplacePlugin[]; [k: string]: unknown },
    });
  }
  return manifests;
}

/** Read ~/.claude/plugins/installed_plugins.json into a flat list of entries */
export function readRegistry(registryPath: string): RegistryEntry[] {
  const abs = expandHome(registryPath);
  const raw = readJsonOrNull<{ plugins?: Record<string, Array<Record<string, unknown>>> }>(abs);
  if (!raw || !raw.plugins) return [];

  const entries: RegistryEntry[] = [];
  for (const [key, arr] of Object.entries(raw.plugins)) {
    if (!Array.isArray(arr)) continue;
    for (const e of arr) {
      if (typeof e.installPath === 'string' && typeof e.version === 'string') {
        entries.push({
          key,
          installPath: e.installPath,
          version: e.version,
          raw: e,
        });
      }
    }
  }
  return entries;
}
