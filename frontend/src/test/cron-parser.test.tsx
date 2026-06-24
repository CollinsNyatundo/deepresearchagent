import { describe, it, expect } from 'vitest'
import { parseCronExpression, getNextRunDates, isValidCronExpression } from '../lib/cronParser'

describe('Cron Parser', () => {
  it('parses cron expression into fields', () => {
    const result = parseCronExpression('0 9 * * *')
    expect(result.minute).toBe(0)
    expect(result.hour).toBe(9)
  })

  it('validates correct cron expressions', () => {
    expect(isValidCronExpression('0 9 * * *')).toBe(true)
    expect(isValidCronExpression('invalid')).toBe(false)
  })

  it('gets next run dates', () => {
    const dates = getNextRunDates('0 9 * * *', 3)
    expect(dates).toHaveLength(3)
    expect(dates[0].getHours()).toBe(9)
    expect(dates[0].getMinutes()).toBe(0)
  })
})
