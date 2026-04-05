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
  /** Raw plugin.json for passthrough when writing marketplace entries */
  raw: Record<string, unknown>;
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
export function scanSourcePlugins(searchRoots: string[], exclude: string[]): SourcePlugin[] {
  const plugins: SourcePlugin[] = [];
  const excludeSet = new Set(exclude);

  for (const root of searchRoots) {
    const abs = expandHome(root);
    if (!fs.existsSync(abs)) continue;
    walk(abs, plugins, excludeSet);
  }

  // Sort for stable output
  plugins.sort((a, b) => a.name.localeCompare(b.name));
  return plugins;
}

function walk(dir: string, plugins: SourcePlugin[], exclude: Set<string>): void {
  const pluginJson = path.join(dir, '.claude-plugin', 'plugin.json');
  if (fs.existsSync(pluginJson)) {
    const raw = readJsonOrNull<Record<string, unknown>>(pluginJson);
    if (raw && typeof raw.name === 'string' && typeof raw.version === 'string') {
      plugins.push({
        name: raw.name,
        version: raw.version,
        description: typeof raw.description === 'string' ? raw.description : '',
        sourceDir: dir,
        pluginJsonPath: pluginJson,
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
    walk(path.join(dir, entry.name), plugins, exclude);
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
