import fs from 'node:fs';
import type { Config } from './config.ts';
import type { DriftReport } from './drift.ts';
import type { MarketplaceManifest, SourcePlugin } from './scan.ts';
import { backupFile, expandHome, readJsonOrNull, writeJsonAtomic, collapseHome } from './util.ts';

export interface ApplyResult {
  backups: string[];
  changes: string[];
}

/**
 * Apply fixes: bring marketplace.json and installed_plugins.json in sync with
 * the source versions. Creates backups before any write.
 */
export function applyFixes(
  config: Config,
  drift: DriftReport,
  manifests: MarketplaceManifest[]
): ApplyResult {
  const result: ApplyResult = { backups: [], changes: [] };

  // ---- 1. Marketplace manifests ----
  for (const manifest of manifests) {
    let manifestChanged = false;

    for (const mp of manifest.plugins) {
      const sourcePlugin = drift.plugins.find((p) => p.source.name === mp.name)?.source;
      if (!sourcePlugin) continue;

      if (mp.version !== sourcePlugin.version) {
        const before = mp.version;
        mp.version = sourcePlugin.version;
        // Update source.version semver if present (`^0.7.0` style)
        if (mp.source && typeof mp.source === 'object' && typeof mp.source.version === 'string') {
          if (mp.source.version.startsWith('^') || mp.source.version.startsWith('~')) {
            mp.source.version = mp.source.version[0] + sourcePlugin.version;
          } else {
            mp.source.version = sourcePlugin.version;
          }
        }
        result.changes.push(
          `${collapseHome(manifest.path)}: ${mp.name} ${before} → ${sourcePlugin.version}`
        );
        manifestChanged = true;
      }
    }

    if (manifestChanged) {
      const bak = backupFile(manifest.path);
      if (bak) result.backups.push(bak);
      writeJsonAtomic(manifest.path, manifest.raw);
    }
  }

  // ---- 2. Claude Code registry (installed_plugins.json) ----
  const registryPath = expandHome(config.claudeCodeRegistry);
  const registryRaw = readJsonOrNull<{ plugins: Record<string, Array<Record<string, unknown>>> }>(
    registryPath
  );
  if (registryRaw && registryRaw.plugins) {
    let registryChanged = false;

    for (const plugin of drift.plugins) {
      for (const rm of plugin.registry) {
        if (rm.inSync || rm.ghost) continue;
        const entries = registryRaw.plugins[rm.key];
        if (!Array.isArray(entries)) continue;
        for (const entry of entries) {
          if (entry.installPath === rm.installPath && entry.version !== plugin.source.version) {
            const before = entry.version;
            entry.version = plugin.source.version;
            result.changes.push(
              `registry ${rm.key}: ${before} → ${plugin.source.version}`
            );
            registryChanged = true;
          }
        }
      }
    }

    if (registryChanged) {
      const bak = backupFile(registryPath);
      if (bak) result.backups.push(bak);
      writeJsonAtomic(registryPath, registryRaw);
    }
  }

  return result;
}

/**
 * Update the auto-managed sentinel section in each marketplaceReadmes file.
 * Sentinel markers: <!-- plugin-sync:start --> and <!-- plugin-sync:end -->.
 */
export function updateReadmes(config: Config, drift: DriftReport): string[] {
  const updated: string[] = [];

  for (const readmePath of config.marketplaceReadmes) {
    const abs = expandHome(readmePath);
    if (!fs.existsSync(abs)) continue;

    const content = fs.readFileSync(abs, 'utf-8');
    const startMarker = '<!-- plugin-sync:start -->';
    const endMarker = '<!-- plugin-sync:end -->';

    const newSection = renderReadmeSection(drift);
    let updatedContent: string;

    if (content.includes(startMarker) && content.includes(endMarker)) {
      // Replace existing section
      const before = content.slice(0, content.indexOf(startMarker));
      const after = content.slice(content.indexOf(endMarker) + endMarker.length);
      updatedContent = before + startMarker + '\n' + newSection + '\n' + endMarker + after;
    } else {
      // Append new section
      updatedContent =
        content.trimEnd() + '\n\n' + startMarker + '\n' + newSection + '\n' + endMarker + '\n';
    }

    if (updatedContent !== content) {
      fs.writeFileSync(abs, updatedContent);
      updated.push(collapseHome(abs));
    }
  }

  return updated;
}

function renderReadmeSection(drift: DriftReport): string {
  const lines: string[] = [];
  lines.push('## Current Plugin Versions');
  lines.push('');
  lines.push('| Plugin | Version | Source | Status |');
  lines.push('|---|---|---|---|');

  for (const p of drift.plugins) {
    const sourceDir = collapseHome(p.source.sourceDir);
    const statusIcon =
      p.status === 'in-sync' ? '✅' : p.status === 'orphan' ? '⚪' : '⚠️';
    lines.push(
      `| \`${p.source.name}\` | \`${p.source.version}\` | \`${sourceDir}\` | ${statusIcon} ${p.summary} |`
    );
  }

  lines.push('');
  lines.push(`_Last synced: ${new Date().toISOString()} · Generated by \`plugin-sync readme\`, do not edit by hand._`);

  return lines.join('\n');
}

export interface StateSnapshot {
  generatedAt: string;
  plugins: Record<
    string,
    {
      version: string;
      sourcePath: string;
      marketplaceVersions: Array<{ manifest: string; version: string }>;
      registryEntries: Array<{ key: string; version: string; installPath: string; ghost: boolean }>;
      status: string;
    }
  >;
  orphanRegistry: Array<{ key: string; version: string; installPath: string; reason: string }>;
}

export function writeStateFile(config: Config, drift: DriftReport): string {
  const snapshot: StateSnapshot = {
    generatedAt: new Date().toISOString(),
    plugins: {},
    orphanRegistry: drift.orphanRegistry.map((o) => ({
      key: o.key,
      version: o.version,
      installPath: o.installPath,
      reason: o.reason,
    })),
  };

  for (const p of drift.plugins) {
    snapshot.plugins[p.source.name] = {
      version: p.source.version,
      sourcePath: p.source.sourceDir,
      marketplaceVersions: p.marketplace.map((m) => ({
        manifest: collapseHome(m.manifestPath),
        version: m.version,
      })),
      registryEntries: p.registry.map((r) => ({
        key: r.key,
        version: r.version,
        installPath: r.installPath,
        ghost: r.ghost,
      })),
      status: p.status,
    };
  }

  writeJsonAtomic(config.stateFile, snapshot);
  return expandHome(config.stateFile);
}
