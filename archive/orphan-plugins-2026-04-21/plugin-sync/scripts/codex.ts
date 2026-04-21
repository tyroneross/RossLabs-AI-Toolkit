import fs from 'node:fs';
import path from 'node:path';
import type { SourcePlugin } from './scan.ts';
import { collapseHome } from './util.ts';

export type CodexAuditIssueCode =
  | 'missing-codex-manifest'
  | 'legacy-manifest-only'
  | 'invalid-codex-manifest'
  | 'name-mismatch'
  | 'version-mismatch'
  | 'description-mismatch'
  | 'missing-readme'
  | 'missing-codex-docs'
  | 'missing-codex-surface';

export interface CodexAuditIssue {
  code: CodexAuditIssueCode;
  message: string;
}

export interface CodexAuditPlugin {
  source: SourcePlugin;
  codexManifestPath: string | null;
  legacyCodexManifestPath: string | null;
  readmePath: string | null;
  skillsCount: number;
  hasMcpSurface: boolean;
  hasCodexSurface: boolean;
  issues: CodexAuditIssue[];
  ok: boolean;
  summary: string;
}

export interface CodexAuditReport {
  generatedAt: string;
  plugins: CodexAuditPlugin[];
  hasIssues: boolean;
}

export function auditCodexInstallability(sources: SourcePlugin[]): CodexAuditReport {
  const plugins = sources.map((source) => auditPlugin(source));
  return {
    generatedAt: new Date().toISOString(),
    plugins,
    hasIssues: plugins.some((plugin) => !plugin.ok),
  };
}

function auditPlugin(source: SourcePlugin): CodexAuditPlugin {
  const issues: CodexAuditIssue[] = [];
  const skillsCount = countSkillSurfaces(source.sourceDir);
  const hasMcpSurface = hasMcpConfig(source);
  const hasCodexSurface = skillsCount > 0 || hasMcpSurface;

  if (!hasCodexSurface) {
    issues.push({
      code: 'missing-codex-surface',
      message:
        'No skill or MCP surface detected. Codex plugins should expose reusable workflows via skills or MCP/app integrations.',
    });
  }

  if (!source.codexPluginJsonPath) {
    issues.push({
      code: source.legacyCodexPluginJsonPath ? 'legacy-manifest-only' : 'missing-codex-manifest',
      message: source.legacyCodexPluginJsonPath
        ? 'Found legacy .Codex-plugin/plugin.json only. Add canonical .codex-plugin/plugin.json for Codex installation.'
        : 'Missing .codex-plugin/plugin.json.',
    });
  } else {
    const parsedCodex = readManifest(source.codexPluginJsonPath);
    if (!parsedCodex.ok) {
      issues.push({
        code: 'invalid-codex-manifest',
        message: `Unable to parse ${collapseHome(source.codexPluginJsonPath)}: ${parsedCodex.error}`,
      });
    } else {
      const codexRaw = parsedCodex.data;
      if (typeof codexRaw.name !== 'string' || codexRaw.name !== source.name) {
        issues.push({
          code: 'name-mismatch',
          message: `Codex manifest name must match Claude manifest name (${JSON.stringify(source.name)}).`,
        });
      }
      if (typeof codexRaw.version !== 'string' || codexRaw.version !== source.version) {
        issues.push({
          code: 'version-mismatch',
          message: `Codex manifest version must match Claude manifest version (${JSON.stringify(source.version)}).`,
        });
      }
      const sourceDescription = normalizeText(source.description);
      const codexDescription =
        typeof codexRaw.description === 'string' ? normalizeText(codexRaw.description) : '';
      if (sourceDescription && codexDescription !== sourceDescription) {
        issues.push({
          code: 'description-mismatch',
          message: 'Codex manifest description should match the Claude manifest description.',
        });
      }
    }
  }

  if (!source.readmePath) {
    issues.push({
      code: 'missing-readme',
      message: 'Missing README.md at the package root.',
    });
  } else {
    const readme = fs.readFileSync(source.readmePath, 'utf-8');
    if (!/\bcodex\b/i.test(readme)) {
      issues.push({
        code: 'missing-codex-docs',
        message: 'README.md does not mention Codex installation or usage.',
      });
    }
  }

  return {
    source,
    codexManifestPath: source.codexPluginJsonPath,
    legacyCodexManifestPath: source.legacyCodexPluginJsonPath,
    readmePath: source.readmePath,
    skillsCount,
    hasMcpSurface,
    hasCodexSurface,
    issues,
    ok: issues.length === 0,
    summary:
      issues.length === 0 ? 'codex-installable' : issues.map((issue) => issue.code).join(', '),
  };
}

function countSkillSurfaces(sourceDir: string): number {
  const rootSkill = path.join(sourceDir, 'SKILL.md');
  if (fs.existsSync(rootSkill)) return 1;

  const skillsDir = path.join(sourceDir, 'skills');
  if (!fs.existsSync(skillsDir) || !fs.statSync(skillsDir).isDirectory()) return 0;

  return fs
    .readdirSync(skillsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(skillsDir, entry.name, 'SKILL.md')))
    .length;
}

function hasMcpConfig(source: SourcePlugin): boolean {
  if (typeof source.raw.mcpServers === 'string') return true;
  if (source.raw.mcpServers && typeof source.raw.mcpServers === 'object') return true;
  return fs.existsSync(path.join(source.sourceDir, '.mcp.json'));
}

function readManifest(
  manifestPath: string
): { ok: true; data: Record<string, unknown> } | { ok: false; error: string } {
  try {
    return {
      ok: true,
      data: JSON.parse(fs.readFileSync(manifestPath, 'utf-8')) as Record<string, unknown>,
    };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'unknown error',
    };
  }
}

function normalizeText(value: string): string {
  return value.trim().replace(/\s+/g, ' ');
}
