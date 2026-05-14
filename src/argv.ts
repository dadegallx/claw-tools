import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir, homedir } from 'node:os'
import { join } from 'node:path'
import { randomUUID } from 'node:crypto'
import type { Job } from './schema'

export type { Job }

export function buildArgv(job: Job): string[] {
  const argv: string[] = [
    '-p', job.prompt,
    '--model', job.model ?? 'haiku',
    '--permission-mode', job.permission_mode ?? 'dontAsk',
    '--max-budget-usd', String(job.max_budget_usd ?? 0.5),
    '--effort', job.effort ?? 'low',
    '--output-format', 'json',
    '--no-session-persistence',
  ]
  if (job.mcps && job.mcps.length > 0) {
    argv.push('--strict-mcp-config', '--mcp-config', writeFilteredMcpConfig(job.mcps))
  }
  return argv
}

function readUserMcpServers(): Record<string, unknown> {
  const candidates = [
    join(homedir(), '.claude.json'),
    join(homedir(), '.claude', 'mcp.json'),
  ]
  for (const path of candidates) {
    if (!existsSync(path)) continue
    try {
      const parsed = JSON.parse(readFileSync(path, 'utf8'))
      if (parsed && typeof parsed === 'object' && parsed.mcpServers && typeof parsed.mcpServers === 'object') {
        return parsed.mcpServers as Record<string, unknown>
      }
    } catch {
      // ignore, try next
    }
  }
  return {}
}

export function writeFilteredMcpConfig(mcps: string[]): string {
  const all = readUserMcpServers()
  const filtered: Record<string, unknown> = {}
  for (const name of mcps) {
    if (name in all) filtered[name] = all[name]
  }
  const path = join(tmpdir(), `scheduler-mcp-${randomUUID()}.json`)
  writeFileSync(path, JSON.stringify({ mcpServers: filtered }, null, 2))
  return path
}
