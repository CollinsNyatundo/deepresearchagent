import { useMemo } from 'react'
import { countTokens, estimateCost, formatTokenCount } from '../lib/tokenizer'

interface TokenCounterProps {
  text: string
  model?: string
  maxTokens?: number
}

export function TokenCounter({ text, model = 'gpt-4', maxTokens }: TokenCounterProps) {
  const tokenCount = useMemo(() => countTokens(text), [text])
  const cost = useMemo(() => estimateCost(tokenCount, model), [tokenCount, model])
  const isOverLimit = maxTokens ? tokenCount > maxTokens * 0.9 : false
  const isCritical = maxTokens ? tokenCount > maxTokens * 0.95 : false

  return (
    <div className="flex items-center gap-3 text-xs">
      <span data-testid="token-count" className={isCritical ? 'text-[#c45a5a] font-semibold' : isOverLimit ? 'text-[#f59e0b]' : 'text-[#c4c6d8]/60'}>
        {formatTokenCount(tokenCount)}
      </span>
      {model && (
        <span className="text-[#c4c6d8]/40">
          ≈ ${cost.toFixed(4)}
        </span>
      )}
      {isOverLimit && (
        <span data-testid="token-warning" className={isCritical ? 'text-[#c45a5a] font-semibold' : 'text-[#f59e0b]'}>
          {isCritical ? '⚠️ Over limit!' : '⚠️ Approaching limit'}
        </span>
      )}
    </div>
  )
}