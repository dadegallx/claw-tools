import { Cron, type CronOptions } from 'croner'

export type { Cron } from 'croner'

export type CronValidationResult =
  | { valid: true }
  | { valid: false, error: string }

export function validateCron(expr: string): CronValidationResult {
  const trimmed = expr.trim()
  if (trimmed.length === 0) {
    return { valid: false, error: 'Cron expression is empty' }
  }
  if (trimmed.split(/\s+/).length !== 5) {
    return { valid: false, error: 'Cron expression must have exactly 5 fields (minute hour day month weekday)' }
  }
  try {
    new Cron(trimmed, { paused: true })
    return { valid: true }
  } catch (e) {
    return { valid: false, error: e instanceof Error ? e.message : String(e) }
  }
}

export function nextFireTimes(expr: string, n: number): Date[] {
  const check = validateCron(expr)
  if (!check.valid) throw new Error(check.error)
  return new Cron(expr, { paused: true }).nextRuns(n)
}

export function makeCron(
  expr: string,
  callback: () => void | Promise<void>,
  options: CronOptions = {},
): Cron {
  const check = validateCron(expr)
  if (!check.valid) throw new Error(check.error)
  return new Cron(expr, options, callback)
}
