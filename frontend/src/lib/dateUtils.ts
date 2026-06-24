import { format, parseISO, isValid } from 'date-fns'

export function formatDate(date: string | Date, formatStr: string = 'yyyy-MM-dd HH:mm'): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return isValid(d) ? format(d, formatStr) : 'Invalid date'
}
