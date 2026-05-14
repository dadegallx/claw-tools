import { test, expect, describe, beforeEach, afterEach } from 'bun:test'
import { writeFileSync, mkdtempSync, rmSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { JobsFileSchema, loadJobs } from '../src/schema'

describe('JobsFileSchema', () => {
  test('accepts minimal valid job', () => {
    const result = JobsFileSchema.safeParse({
      jobs: [{ name: 'test', cron: '0 8 * * *', prompt: 'hello' }]
    })
    expect(result.success).toBe(true)
    if (result.success) {
      // Defaults applied
      expect(result.data.jobs[0].recurring).toBe(true)
      expect(result.data.jobs[0].model).toBe('haiku')
      expect(result.data.jobs[0].mcps).toEqual([])
      expect(result.data.jobs[0].max_budget_usd).toBe(0.5)
      expect(result.data.jobs[0].permission_mode).toBe('dontAsk')
      expect(result.data.jobs[0].effort).toBe('low')
      expect(result.data.jobs[0].timeout_seconds).toBe(300)
      expect(result.data.jobs[0].report_back).toBe('summary')
      expect(result.data.jobs[0].enabled).toBe(true)
    }
  })

  test('accepts fully specified job', () => {
    const result = JobsFileSchema.safeParse({
      jobs: [{
        name: 'daily-budget', cron: '57 8 * * *', recurring: true,
        prompt: 'do the thing', model: 'sonnet',
        mcps: ['telegram', 'lunch-money'],
        max_budget_usd: 0.3, permission_mode: 'dontAsk', effort: 'medium',
        timeout_seconds: 120, report_back: 'full', enabled: true
      }]
    })
    expect(result.success).toBe(true)
  })

  test('rejects missing required fields', () => {
    expect(JobsFileSchema.safeParse({ jobs: [{}] }).success).toBe(false)
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x' }] }).success).toBe(false)
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *' }] }).success).toBe(false)
  })

  test('rejects invalid name format', () => {
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'has spaces', cron: '* * * * *', prompt: 'x' }] }).success).toBe(false)
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'has/slash', cron: '* * * * *', prompt: 'x' }] }).success).toBe(false)
  })

  test('rejects invalid cron', () => {
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: 'garbage', prompt: 'x' }] }).success).toBe(false)
  })

  test('rejects 6-field cron (seconds not supported)', () => {
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '0 0 8 * * *', prompt: 'x' }] }).success).toBe(false)
  })

  test('rejects negative or zero budget', () => {
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *', prompt: 'x', max_budget_usd: -1 }] }).success).toBe(false)
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *', prompt: 'x', max_budget_usd: 0 }] }).success).toBe(false)
  })

  test('rejects unknown effort / permission_mode / report_back', () => {
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *', prompt: 'x', effort: 'turbo' }] }).success).toBe(false)
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *', prompt: 'x', permission_mode: 'yolo' }] }).success).toBe(false)
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *', prompt: 'x', report_back: 'shout' }] }).success).toBe(false)
  })

  test('rejects duplicate job names', () => {
    const result = JobsFileSchema.safeParse({
      jobs: [
        { name: 'dup', cron: '* * * * *', prompt: 'a' },
        { name: 'dup', cron: '* * * * *', prompt: 'b' }
      ]
    })
    expect(result.success).toBe(false)
  })

  test('rejects timeout out of range', () => {
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *', prompt: 'x', timeout_seconds: 0 }] }).success).toBe(false)
    expect(JobsFileSchema.safeParse({ jobs: [{ name: 'x', cron: '* * * * *', prompt: 'x', timeout_seconds: 4000 }] }).success).toBe(false)
  })
})

describe('loadJobs', () => {
  let tmpDir: string
  let jobsFile: string

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'sched-test-'))
    jobsFile = join(tmpDir, 'jobs.json')
  })

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true })
  })

  test('returns empty job list when file is missing', () => {
    const result = loadJobs(jobsFile)
    expect(result.jobs).toEqual([])
  })

  test('parses a valid file', () => {
    writeFileSync(jobsFile, JSON.stringify({ jobs: [{ name: 'x', cron: '0 8 * * *', prompt: 'hi' }] }))
    const result = loadJobs(jobsFile)
    expect(result.jobs).toHaveLength(1)
    expect(result.jobs[0].name).toBe('x')
  })

  test('renames corrupt file to .corrupt-<ts> and returns empty', () => {
    writeFileSync(jobsFile, 'not json')
    const result = loadJobs(jobsFile)
    expect(result.jobs).toEqual([])
    const files = readdirSync(tmpDir)
    expect(files.some(f => f.startsWith('jobs.json.corrupt-'))).toBe(true)
  })

  test('renames schema-invalid file and returns empty', () => {
    writeFileSync(jobsFile, JSON.stringify({ jobs: [{ name: 'has space', cron: '* * * * *', prompt: 'x' }] }))
    const result = loadJobs(jobsFile)
    expect(result.jobs).toEqual([])
  })

  test('parses the bundled fixture file', () => {
    const fixture = join(import.meta.dir, 'fixtures', 'jobs.example.json')
    const result = loadJobs(fixture)
    expect(result.jobs.length).toBeGreaterThan(0)
    expect(result.jobs[0].name).toBe('daily-budget')
  })
})
