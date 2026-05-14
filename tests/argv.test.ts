import { test, expect, describe } from 'bun:test'
import { buildArgv } from '../src/argv'
import type { Job } from '../src/argv'

const baseJob: Job = {
  name: 'test', cron: '0 8 * * *', prompt: 'hello',
  recurring: true, model: 'haiku', mcps: [], max_budget_usd: 0.5,
  permission_mode: 'dontAsk', effort: 'low', timeout_seconds: 300,
  report_back: 'summary', enabled: true
}

describe('buildArgv', () => {
  test('emits all mandatory flags for a minimal job', () => {
    const argv = buildArgv(baseJob)
    expect(argv).toContain('-p')
    expect(argv).toContain('hello')
    expect(argv).toContain('--model')
    expect(argv).toContain('haiku')
    expect(argv).toContain('--permission-mode')
    expect(argv).toContain('dontAsk')
    expect(argv).toContain('--max-budget-usd')
    expect(argv).toContain('0.5')
    expect(argv).toContain('--effort')
    expect(argv).toContain('low')
    expect(argv).toContain('--output-format')
    expect(argv).toContain('json')
    expect(argv).toContain('--no-session-persistence')
  })

  test('honors model override', () => {
    const argv = buildArgv({ ...baseJob, model: 'sonnet' })
    const modelIdx = argv.indexOf('--model')
    expect(argv[modelIdx + 1]).toBe('sonnet')
  })

  test('honors all field overrides', () => {
    const argv = buildArgv({
      ...baseJob, model: 'opus', permission_mode: 'auto',
      max_budget_usd: 1.5, effort: 'high'
    })
    expect(argv[argv.indexOf('--model') + 1]).toBe('opus')
    expect(argv[argv.indexOf('--permission-mode') + 1]).toBe('auto')
    expect(argv[argv.indexOf('--max-budget-usd') + 1]).toBe('1.5')
    expect(argv[argv.indexOf('--effort') + 1]).toBe('high')
  })

  test('omits mcp flags when mcps is empty', () => {
    const argv = buildArgv(baseJob)
    expect(argv).not.toContain('--strict-mcp-config')
    expect(argv).not.toContain('--mcp-config')
  })

  test('appends --strict-mcp-config + --mcp-config when mcps is non-empty', () => {
    const argv = buildArgv({ ...baseJob, mcps: ['telegram', 'lunch-money'] })
    expect(argv).toContain('--strict-mcp-config')
    const idx = argv.indexOf('--mcp-config')
    expect(idx).toBeGreaterThan(-1)
    // The value after --mcp-config should be a path string
    expect(typeof argv[idx + 1]).toBe('string')
    expect(argv[idx + 1].length).toBeGreaterThan(0)
  })

  test('prompt is passed verbatim, no escaping', () => {
    const tricky = `hello "world" and 'quotes' and \\backslashes`
    const argv = buildArgv({ ...baseJob, prompt: tricky })
    expect(argv).toContain(tricky)
    // Should appear immediately after -p
    expect(argv[argv.indexOf('-p') + 1]).toBe(tricky)
  })

  test('argv contains no undefined entries', () => {
    const argv = buildArgv(baseJob)
    for (const entry of argv) {
      expect(entry).toBeDefined()
      expect(typeof entry).toBe('string')
    }
  })
})

describe('writeFilteredMcpConfig', () => {
  test('returns a path to a temp file', async () => {
    const { writeFilteredMcpConfig } = await import('../src/argv')
    const path = writeFilteredMcpConfig(['telegram'])
    expect(path).toBeTypeOf('string')
    expect(path.length).toBeGreaterThan(0)
    // File should exist
    const { readFileSync, existsSync } = await import('node:fs')
    expect(existsSync(path)).toBe(true)
    // Contents are valid JSON with mcpServers key
    const content = JSON.parse(readFileSync(path, 'utf8'))
    expect(content.mcpServers).toBeDefined()
  })
})
