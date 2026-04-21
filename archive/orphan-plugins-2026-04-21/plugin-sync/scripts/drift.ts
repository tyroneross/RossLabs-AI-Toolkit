import fs from 'node:fs';
import path from 'node:path';
import type { MarketplaceManifest, RegistryEntry, SourcePlugin } from './scan.ts';
import { expandHome } from './util.ts';

export type Status = 'in-sync' | 'drift' | 'orphan' | 'source-missing';

export interface MarketplaceMatch {
  manifestPath: string;
  version: string;
  inSync: boolean;
}

export interface RegistryMatch {
  key: string;
  installPath: string;
  version: string;
  inSync: boolean;
  /** Registry installPath no longer exists on disk */
  ghost: boolean;
}

export interface PluginDrift {
  source: SourcePlugin;
  status: Status;
  marketplace: MarketplaceMatch[];
  registry: RegistryMatch[];
  /** Human-readable one-line description of the drift, if any */
  summary: string;
}

export interface OrphanRegistryEntry {
  key: string;
  installPath: string;
  version: string;
  reason: 'source-missing' | 'not-in-config';
}

export interface DriftReport {
  plugins: PluginDrift[];
  /** Registry entries that don't match any source plugin */
  orphanRegistry: OrphanRegistryEntry[];
  /** True if any plugin has status !== 'in-sync' */
  hasDrift: boolean;
}

/**
 * Cross-reference source plugins against marketplace manifests and the
 * installed_plugins.json registry. Produces a structured drift report.
 */
export function computeDrift(
  sources: SourcePlugin[],
  manifests: MarketplaceManifest[],
  registry: RegistryEntry[]
): DriftReport {
  const plugins: PluginDrift[] = [];
  const matchedRegistryKeys = new Set<string>();

  for (const source of sources) {
    // Marketplace matches — name equality
    const marketplaceMatches: MarketplaceMatch[] = [];
    for (const manifest of manifests) {
      const entry = manifest.plugins.find((p) => p.name === source.name);
      if (entry) {
        marketplaceMatches.push({
          manifestPath: manifest.path,
          version: entry.version,
          inSync: entry.version === source.version,
        });
      }
    }

    // Registry matches — installPath equals sourceDir (either exactly or the plugin
    // installed from the source path). Also match by `name@*` key prefix for extra safety.
    const registryMatches: RegistryMatch[] = [];
    const resolvedSource = path.resolve(source.sourceDir);
    for (const r of registry) {
      const resolvedInstall = path.resolve(expandHome(r.installPath));
      const installPathMatch = resolvedInstall === resolvedSource;
      const keyNameMatch = r.key.split('@')[0] === source.name;
      if (installPathMatch || keyNameMatch) {
        const ghost = !fs.existsSync(resolvedInstall);
        registryMatches.push({
          key: r.key,
          installPath: r.installPath,
          version: r.version,
          inSync: r.version === source.version && !ghost,
          ghost,
        });
        matchedRegistryKeys.add(r.key);
      }
    }

    // Determine overall status
    let status: Status = 'in-sync';
    const driftParts: string[] = [];

    if (marketplaceMatches.length === 0 && registryMatches.length === 0) {
      status = 'orphan';
      driftParts.push('not in any marketplace or registry');
    } else {
      for (const m of marketplaceMatches) {
        if (!m.inSync) {
          status = 'drift';
          driftParts.push(`marketplace=${m.version}`);
        }
      }
      for (const r of registryMatches) {
        if (r.ghost) {
          status = 'drift';
          driftParts.push(`registry "${r.key}" ghost path`);
        } else if (!r.inSync) {
          status = 'drift';
          driftParts.push(`registry "${r.key}"=${r.version}`);
        }
      }
    }

    const summary =
      status === 'in-sync'
        ? 'in sync'
        : status === 'orphan'
        ? driftParts[0]
        : `source=${source.version}; ${driftParts.join(', ')}`;

    plugins.push({ source, status, marketplace: marketplaceMatches, registry: registryMatches, summary });
  }

  // Orphan registry entries — in registry but no matching source plugin
  const orphanRegistry: OrphanRegistryEntry[] = [];
  for (const r of registry) {
    if (matchedRegistryKeys.has(r.key)) continue;
    const resolvedInstall = path.resolve(expandHome(r.installPath));
    const reason: OrphanRegistryEntry['reason'] = fs.existsSync(resolvedInstall)
      ? 'not-in-config'
      : 'source-missing';
    orphanRegistry.push({
      key: r.key,
      installPath: r.installPath,
      version: r.version,
      reason,
    });
  }

  const hasDrift = plugins.some((p) => p.status !== 'in-sync') || orphanRegistry.length > 0;

  return { plugins, orphanRegistry, hasDrift };
}
