import CronExpressionParser from 'cron-parser'

export interface CronFields {
  minute: number
  hour: number
  dayOfMonth: number
  month: number
  dayOfWeek: number
}

export function parseCronExpression(cron: string): CronFields {
  try {
    const parsed = CronExpressionParser.parse(cron)
    const fields = parsed.fields
    const extract = (field: { options: { rawValue: string } }): number => {
      const raw = field.options.rawValue
      if (raw === '*') return -1
      const num = parseInt(raw, 10)
      return isNaN(num) ? 0 : num
    }
    return {
      minute: extract(fields.minute as any),
      hour: extract(fields.hour as any),
      dayOfMonth: extract(fields.dayOfMonth as any),
      month: extract(fields.month as any),
      dayOfWeek: extract(fields.dayOfWeek as any),
    }
  } catch {
    return { minute: 0, hour: 0, dayOfMonth: 1, month: 1, dayOfWeek: 0 }
  }
}

export function isValidCronExpression(cron: string): boolean {
  try {
    CronExpressionParser.parse(cron)
    return true
  } catch {
    return false
  }
}

export function getNextRunDates(cron: string, count: number = 5): Date[] {
  try {
    const interval = CronExpressionParser.parse(cron)
    const dates: Date[] = []
    for (let i = 0; i < count; i++) {
      dates.push(interval.next().toDate())
    }
    return dates
  } catch {
    return []
  }
}
