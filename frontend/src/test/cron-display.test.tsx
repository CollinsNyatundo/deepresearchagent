import { describe, it, expect } from 'vitest'
import { formatCronExpression, isValidCron } from '../lib/cronDisplay'

describe('Cron Human-Readable Display', () => {
  it('formats daily cron expression', () => {
    const result = formatCronExpression('0 9 * * *')
    expect(result).toContain('9:00 AM')
  })

  it('formats weekly cron expression', () => {
    const result = formatCronExpression('0 9 * * 1')
    expect(result.toLowerCase()).toContain('monday')
  })

  it('returns invalid for bad expressions', () => {
    const result = formatCronExpression('invalid')
    expect(result).toBe('Invalid cron expression')
  })

  it('validates correct cron expressions', () => {
    expect(isValidCron('0 9 * * *')).toBe(true)
    expect(isValidCron('invalid')).toBe(false)
  })
})
