import { test, expect, describe } from 'bun:test'
import { validateCron, nextFireTimes, makeCron } from '../src/cron'

describe('validateCron', () => {
  test('accepts standard 5-field expressions', () => {
    expect(validateCron('0 8 * * *').valid).toBe(true)
    expect(validateCron('*/5 * * * *').valid).toBe(true)
    expect(validateCron('57 8 * * 1-5').valid).toBe(true)
    expect(validateCron('0 0 1 1 *').valid).toBe(true)
  })

  test('rejects malformed expressions', () => {
    expect(validateCron('not a cron').valid).toBe(false)
    expect(validateCron('').valid).toBe(false)
    expect(validateCron('99 99 99 99 99').valid).toBe(false)
  })

  test('rejects non-5-field expressions (6-field with seconds is NOT supported)', () => {
    // croner supports 6-field by default; we want to reject it for consistency with CronCreate
    expect(validateCron('0 0 8 * * *').valid).toBe(false)
  })

  test('returned error message is human-readable', () => {
    const result = validateCron('not a cron')
    if (!result.valid) {
      expect(result.error).toBeTypeOf('string')
      expect(result.error.length).toBeGreaterThan(0)
    }
  })
})

describe('nextFireTimes', () => {
  test('returns N future Dates for a daily cron', () => {
    const fires = nextFireTimes('0 8 * * *', 3)
    expect(fires).toHaveLength(3)
    for (const f of fires) expect(f).toBeInstanceOf(Date)
    // Each fire is later than the previous
    expect(fires[1].getTime()).toBeGreaterThan(fires[0].getTime())
    expect(fires[2].getTime()).toBeGreaterThan(fires[1].getTime())
    // All fires are at 8:00 local time
    for (const f of fires) {
      expect(f.getHours()).toBe(8)
      expect(f.getMinutes()).toBe(0)
    }
  })

  test('weekday-only cron skips weekends', () => {
    const fires = nextFireTimes('0 9 * * 1-5', 5)
    for (const f of fires) {
      const day = f.getDay()  // 0=Sun, 6=Sat
      expect(day).toBeGreaterThanOrEqual(1)
      expect(day).toBeLessThanOrEqual(5)
    }
  })

  test('every-5-min cron fires close together', () => {
    const fires = nextFireTimes('*/5 * * * *', 2)
    const delta = fires[1].getTime() - fires[0].getTime()
    expect(delta).toBe(5 * 60 * 1000)
  })

  test('throws on invalid cron', () => {
    expect(() => nextFireTimes('garbage', 3)).toThrow()
  })
})

describe('makeCron', () => {
  test('creates a paused Cron instance bound to a callback', () => {
    let fired = 0
    const cron = makeCron('*/5 * * * *', () => { fired++ }, { paused: true })
    expect(cron).toBeDefined()
    expect(typeof cron.stop).toBe('function')
    cron.stop()  // cleanup
  })

  test('rejects invalid cron at construction', () => {
    expect(() => makeCron('garbage', () => {})).toThrow()
  })
})
