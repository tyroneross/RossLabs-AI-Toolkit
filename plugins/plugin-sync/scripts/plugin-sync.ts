#!/usr/bin/env -S npx tsx
import { Command } from 'commander';
import { loadConfig, ConfigMissingError, DEFAULT_CONFIG_PATH } from './config.ts';
import { scanSourcePlugins, readMarketplaceManifests, readRegistry } from './scan.ts';
import { computeDrift, type DriftReport } from './drift.ts';
import { applyFixes, updateReadmes, writeStateFile } from './apply.ts';
import { installHooks, uninstallHooks } from './hooks.ts';
import { color, collapseHome } from './util.ts';

const program = new Command();

program
  .name('plugin-sync')
  .description('Track and sync local Claude Code plugins across source / marketplace / registry')
  .version('0.1.0')
  .option('-c, --config <path>', 'path to config.json', DEFAULT_CONFIG_PATH);

// ---- status ----
program
  .command('status')
  .description('Print drift report (read-only)')
  .option('--json', 'emit machine-readable JSON instead of a table')
  .action((opts) => {
    const drift = gather();
    if (opts.json) {
      console.log(JSON.stringify(drift, null, 2));
      process.exit(drift.hasDrift ? 1 : 0);
    }
    printStatus(drift);
    process.exit(drift.hasDrift ? 1 : 0);
  });

// ---- fix ----
program
  .command('fix')
  .description('Apply drift fixes — update marketplace.json and installed_plugins.json to match source versions')
  .option('--quiet', 'only print if changes were made')
  .action((opts) => {
    const config = tryLoadConfig();
    const sources = scanSourcePlugins(config.searchRoots, config.exclude);
    const manifests = readMarketplaceManifests(config.marketplaceManifests);
    const registry = readRegistry(config.claudeCodeRegistry);
    const drift = computeDrift(sources, manifests, registry);
    const result = applyFixes(config, drift, manifests);

    if (result.changes.length === 0) {
      if (!opts.quiet) {
        console.log(color('✓ No drift — nothing to fix.', 'green'));
      }
      return;
    }

    console.log(color(`Applied ${result.changes.length} fix(es):`, 'bold'));
    for (const c of result.changes) console.log(`  • ${c}`);
    if (result.backups.length > 0) {
      console.log(color(`\nBackups:`, 'dim'));
      for (const b of result.backups) console.log(`  ${collapseHome(b)}`);
    }
  });

// ---- state ----
program
  .command('state')
  .description('Write snapshot to state.json (dashboard input)')
  .action(() => {
    const config = tryLoadConfig();
    const sources = scanSourcePlugins(config.searchRoots, config.exclude);
    const manifests = readMarketplaceManifests(config.marketplaceManifests);
    const registry = readRegistry(config.claudeCodeRegistry);
    const drift = computeDrift(sources, manifests, registry);
    const path = writeStateFile(config, drift);
    console.log(color(`✓ Wrote ${collapseHome(path)}`, 'green'));
  });

// ---- readme ----
program
  .command('readme')
  .description('Update auto-managed sections in marketplace README files')
  .action(() => {
    const config = tryLoadConfig();
    const sources = scanSourcePlugins(config.searchRoots, config.exclude);
    const manifests = readMarketplaceManifests(config.marketplaceManifests);
    const registry = readRegistry(config.claudeCodeRegistry);
    const drift = computeDrift(sources, manifests, registry);
    const updated = updateReadmes(config, drift);

    if (updated.length === 0) {
      console.log(color('No README changes.', 'dim'));
      return;
    }
    console.log(color(`✓ Updated ${updated.length} README file(s):`, 'green'));
    for (const u of updated) console.log(`  ${u}`);
  });

// ---- install-hooks ----
program
  .command('install-hooks')
  .description('Install post-commit hooks in every source plugin repo')
  .action(() => {
    const config = tryLoadConfig();
    const sources = scanSourcePlugins(config.searchRoots, config.exclude);
    const result = installHooks(sources);

    if (result.installed.length > 0) {
      console.log(color(`✓ Installed post-commit hooks in ${result.installed.length} repo(s):`, 'green'));
      for (const p of result.installed) console.log(`  • ${p}`);
    }
    if (result.skipped.length > 0) {
      console.log(color(`\nSkipped ${result.skipped.length}:`, 'yellow'));
      for (const s of result.skipped) console.log(`  • ${s.plugin} — ${s.reason}`);
    }
  });

// ---- uninstall-hooks ----
program
  .command('uninstall-hooks')
  .description('Remove plugin-sync post-commit hooks from every source plugin repo')
  .action(() => {
    const config = tryLoadConfig();
    const sources = scanSourcePlugins(config.searchRoots, config.exclude);
    const result = uninstallHooks(sources);

    if (result.removed.length > 0) {
      console.log(color(`✓ Removed hooks from ${result.removed.length} repo(s):`, 'green'));
      for (const p of result.removed) console.log(`  • ${p}`);
    }
    if (result.skipped.length > 0) {
      console.log(color(`\nSkipped:`, 'dim'));
      for (const s of result.skipped) console.log(`  • ${s.plugin} — ${s.reason}`);
    }
    if (result.removed.length === 0 && result.skipped.length === 0) {
      console.log(color('No plugin-sync hooks installed.', 'dim'));
    }
  });

// ---- helpers ----
function tryLoadConfig() {
  try {
    return loadConfig(program.opts().config);
  } catch (err) {
    if (err instanceof ConfigMissingError) {
      console.error(color(`error: ${err.message}`, 'red'));
      console.error(
        color(
          `\nQuick start: copy config.example.json to ${err.path} and edit the searchRoots.`,
          'dim'
        )
      );
      process.exit(2);
    }
    throw err;
  }
}

function gather(): DriftReport {
  const config = tryLoadConfig();
  const sources = scanSourcePlugins(config.searchRoots, config.exclude);
  const manifests = readMarketplaceManifests(config.marketplaceManifests);
  const registry = readRegistry(config.claudeCodeRegistry);
  return computeDrift(sources, manifests, registry);
}

function printStatus(drift: DriftReport): void {
  if (drift.plugins.length === 0) {
    console.log(color('No source plugins found in configured searchRoots.', 'yellow'));
    return;
  }

  // Column widths
  const nameW = Math.max(6, ...drift.plugins.map((p) => p.source.name.length));
  const verW = Math.max(7, ...drift.plugins.map((p) => p.source.version.length));
  const pathW = Math.max(
    6,
    ...drift.plugins.map((p) => collapseHome(p.source.sourceDir).length)
  );

  const header = `${pad('plugin', nameW)}  ${pad('version', verW)}  ${pad('source', pathW)}  status`;
  console.log(color(header, 'bold'));
  console.log(color('─'.repeat(header.length), 'dim'));

  for (const p of drift.plugins) {
    const icon =
      p.status === 'in-sync' ? color('✓', 'green') : p.status === 'orphan' ? color('○', 'dim') : color('✗', 'red');
    const statusText =
      p.status === 'in-sync'
        ? color('in sync', 'green')
        : p.status === 'orphan'
        ? color(p.summary, 'dim')
        : color(p.summary, 'red');
    console.log(
      `${pad(p.source.name, nameW)}  ${pad(p.source.version, verW)}  ${pad(
        collapseHome(p.source.sourceDir),
        pathW
      )}  ${icon} ${statusText}`
    );
  }

  if (drift.orphanRegistry.length > 0) {
    console.log(color('\nOrphan registry entries:', 'yellow'));
    for (const o of drift.orphanRegistry) {
      console.log(
        `  ${color('•', 'yellow')} ${o.key} → ${collapseHome(o.installPath)} (${o.reason})`
      );
    }
  }

  console.log();
  if (drift.hasDrift) {
    console.log(color('Drift detected — run `plugin-sync fix` to apply corrections.', 'yellow'));
  } else {
    console.log(color('✓ Everything in sync.', 'green'));
  }
}

function pad(s: string, w: number): string {
  return s + ' '.repeat(Math.max(0, w - s.length));
}

program.parse();
