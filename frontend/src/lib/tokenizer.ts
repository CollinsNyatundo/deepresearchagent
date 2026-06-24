import { encode } from 'gpt-tokenizer'

export function countTokens(text: string): number {
  try {
    const tokens = encode(text)
    return tokens.length
  } catch {
    return Math.ceil(text.length / 4)
  }
}

export function estimateCost(tokenCount: number, model: string = 'gpt-4'): number {
  const rates: Record<string, number> = {
    'gpt-4': 0.03,
    'gpt-4-turbo': 0.01,
    'gpt-3.5-turbo': 0.0015,
  }
  const rate = rates[model] || 0.01
  return (tokenCount / 1000) * rate
}

export function formatTokenCount(count: number): string {
  if (count < 1000) {
    return `${count} tokens`
  }
  return `${(count / 1000).toFixed(1)}k tokens`
}
