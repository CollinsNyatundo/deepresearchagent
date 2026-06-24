import cronstrue from 'cronstrue'

export function formatCronExpression(cron: string): string {
  try {
    return cronstrue.toString(cron)
  } catch {
    return 'Invalid cron expression'
  }
}

export function isValidCron(cron: string): boolean {
  try {
    cronstrue.toString(cron)
    return true
  } catch {
    return false
  }
}
