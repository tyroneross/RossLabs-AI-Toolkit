import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

export function expandHome(p: string): string {
  if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
  if (p === '~') return os.homedir();
  return p;
}

export function collapseHome(p: string): string {
  const home = os.homedir();
  if (p === home) return '~';
  if (p.startsWith(home + path.sep)) return '~/' + p.slice(home.length + 1);
  return p;
}

export function readJson<T = unknown>(filePath: string): T {
  const raw = fs.readFileSync(expandHome(filePath), 'utf-8');
  return JSON.parse(raw) as T;
}

export function readJsonOrNull<T = unknown>(filePath: string): T | null {
  try {
    return readJson<T>(filePath);
  } catch {
    return null;
  }
}

/**
 * Write JSON atomically: write to a tmp file in the same dir, then rename.
 * Prevents half-written files on crash or interrupt.
 */
export function writeJsonAtomic(filePath: string, data: unknown, indent = 2): void {
  const abs = expandHome(filePath);
  const dir = path.dirname(abs);
  fs.mkdirSync(dir, { recursive: true });
  const tmp = `${abs}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, JSON.stringify(data, null, indent) + '\n');
  fs.renameSync(tmp, abs);
}

export function backupFile(filePath: string): string | null {
  const abs = expandHome(filePath);
  if (!fs.existsSync(abs)) return null;
  const bak = `${abs}.bak-${Date.now()}`;
  fs.copyFileSync(abs, bak);
  return bak;
}

export function fileExists(filePath: string): boolean {
  try {
    return fs.existsSync(expandHome(filePath));
  } catch {
    return false;
  }
}

export function dirExists(dirPath: string): boolean {
  try {
    return fs.statSync(expandHome(dirPath)).isDirectory();
  } catch {
    return false;
  }
}

/** Color helpers — avoid a chalk dependency */
export const c = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
};

export function color(text: string, style: keyof typeof c): string {
  if (!process.stdout.isTTY) return text;
  return `${c[style]}${text}${c.reset}`;
}
