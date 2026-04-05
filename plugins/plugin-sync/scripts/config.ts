import { z } from 'zod';
import { expandHome, fileExists, readJson } from './util.ts';

/**
 * plugin-sync config — lives at ~/.config/claude-plugins/config.json.
 * Not committed to any plugin repo. Scoped to the tool author's machine.
 */
export const ConfigSchema = z.object({
  /** Directories to walk looking for `.claude-plugin/plugin.json` files */
  searchRoots: z.array(z.string()).min(1),

  /** Marketplace manifests to keep in sync with source versions */
  marketplaceManifests: z.array(z.string()).default([]),

  /** README files that contain a <!-- plugin-sync:start --> / <!-- plugin-sync:end --> section */
  marketplaceReadmes: z.array(z.string()).default([]),

  /** Path to Claude Code's installed_plugins.json registry */
  claudeCodeRegistry: z.string().default('~/.claude/plugins/installed_plugins.json'),

  /** Where to write the state snapshot on `plugin-sync state` */
  stateFile: z.string().default('~/.config/claude-plugins/state.json'),

  /** Directories skipped during search-root walks */
  exclude: z.array(z.string()).default(['node_modules', '.git', 'dist', '.next', 'coverage', '.worktrees']),
});

export type Config = z.infer<typeof ConfigSchema>;

export const DEFAULT_CONFIG_PATH = '~/.config/claude-plugins/config.json';

export function loadConfig(configPath: string = DEFAULT_CONFIG_PATH): Config {
  const expanded = expandHome(configPath);
  if (!fileExists(expanded)) {
    throw new ConfigMissingError(expanded);
  }
  const raw = readJson(expanded);
  const parsed = ConfigSchema.safeParse(raw);
  if (!parsed.success) {
    throw new Error(
      `Invalid config at ${expanded}:\n${parsed.error.issues
        .map((i) => `  - ${i.path.join('.')}: ${i.message}`)
        .join('\n')}`
    );
  }
  return parsed.data;
}

export class ConfigMissingError extends Error {
  constructor(public path: string) {
    super(
      `No plugin-sync config at ${path}. This tool is scoped to its author's machine; ` +
        `create the config to enable it. See config.example.json at the plugin-sync plugin root.`
    );
    this.name = 'ConfigMissingError';
  }
}
