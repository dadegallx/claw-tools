import { z } from 'zod'
import { readFileSync, renameSync, existsSync } from 'node:fs'
import { validateCron } from './cron'

const isValidCron = (value: string): boolean => validateCron(value).valid

const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/i

export const JobSchema = z.object({
  name: z
    .string()
    .min(1)
    .regex(NAME_RE, 'name must match /^[a-z0-9][a-z0-9_-]*$/i (no spaces or slashes)'),
  cron: z
    .string()
    .min(1)
    .refine(isValidCron, { message: 'cron must be a valid 5-field expression' }),
  recurring: z.boolean().default(true),
  prompt: z.string().min(1),
  model: z.string().default('haiku'),
  mcps: z.array(z.string()).default([]),
  max_budget_usd: z.number().positive().default(0.5),
  permission_mode: z
    .enum(['acceptEdits', 'auto', 'bypassPermissions', 'default', 'dontAsk', 'plan'])
    .default('dontAsk'),
  effort: z.enum(['low', 'medium', 'high', 'xhigh', 'max']).default('low'),
  timeout_seconds: z.number().positive().max(3600).default(300),
  report_back: z.enum(['summary', 'full', 'silent']).default('summary'),
  enabled: z.boolean().default(true),
})

export const JobsFileSchema = z
  .object({ jobs: z.array(JobSchema) })
  .refine(
    (data) => {
      const names = data.jobs.map((j) => j.name)
      return new Set(names).size === names.length
    },
    { message: 'job names must be unique', path: ['jobs'] }
  )

export type Job = z.infer<typeof JobSchema>
export type JobsFile = z.infer<typeof JobsFileSchema>

/**
 * Read and validate a jobs.json file.
 * - Missing file: returns `{ jobs: [] }`.
 * - Invalid JSON or schema failure: renames the bad file to `${path}.corrupt-<ts>`
 *   and returns `{ jobs: [] }` so the scheduler can keep running.
 */
export function loadJobs(path: string): JobsFile {
  if (!existsSync(path)) return { jobs: [] }

  let raw: string
  try {
    raw = readFileSync(path, 'utf8')
  } catch {
    return { jobs: [] }
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    quarantine(path)
    return { jobs: [] }
  }

  const result = JobsFileSchema.safeParse(parsed)
  if (!result.success) {
    quarantine(path)
    return { jobs: [] }
  }
  return result.data
}

function quarantine(path: string): void {
  try {
    renameSync(path, `${path}.corrupt-${Date.now()}`)
  } catch {
    // best-effort; don't crash the scheduler over a rename failure
  }
}
