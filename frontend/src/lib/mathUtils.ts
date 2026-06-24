import { evaluate } from 'mathjs'

export function safeEvaluate(expression: string): number | string {
  try {
    return evaluate(expression)
  } catch {
    return 'Error'
  }
}
