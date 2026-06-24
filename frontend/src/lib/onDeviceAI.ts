import { pipeline, env } from '@huggingface/transformers'

export interface OnDeviceAIResult {
  text: string
  confidence?: number
}

export interface PIIEntity {
  entity: string
  word: string
  score: number
}

export interface SentimentResult {
  label: string
  score: number
}

let textPipeline: any = null
let piiPipeline: any = null
let sentimentPipeline: any = null

export async function initializeOnDeviceAI() {
  env.cacheDir = 'indexeddb://transformers-cache'
  env.allowLocalModels = true
  env.allowRemoteModels = true
}

export async function initializeTextPipeline() {
  if (!textPipeline) {
    textPipeline = await pipeline('text-generation', 'Xenova/tiny-gpt2', {
      dtype: 'q4',
    })
  }
  return textPipeline
}

export async function detectPII(text: string): Promise<PIIEntity[]> {
  try {
    await initializeOnDeviceAI()
    if (!piiPipeline) {
      piiPipeline = await pipeline('token-classification', 'Xenova/distilbert-base-uncased', {
        dtype: 'q4',
      })
    }
    const results = await piiPipeline(text)
    return results.map((r: any) => ({
      entity: r.entity,
      word: r.word,
      score: r.score,
    }))
  } catch (error) {
    console.error('PII detection error:', error)
    return []
  }
}

export async function analyzeSentiment(text: string): Promise<SentimentResult> {
  try {
    await initializeOnDeviceAI()
    if (!sentimentPipeline) {
      sentimentPipeline = await pipeline('sentiment-analysis', 'Xenova/distilbert-base-uncased-finetuned-sst-2-english', {
        dtype: 'q4',
      })
    }
    const results = await sentimentPipeline(text)
    return results[0] as SentimentResult
  } catch (error) {
    console.error('Sentiment analysis error:', error)
    return { label: 'NEUTRAL', score: 0.5 }
  }
}

export async function generateText(prompt: string, maxLength: number = 50): Promise<OnDeviceAIResult[]> {
  try {
    const generator = await initializeTextPipeline()
    const results = await generator(prompt, {
      max_new_tokens: maxLength,
      temperature: 0.7,
      do_sample: true,
    })
    return results.map((r: any) => ({
      text: r.generated_text,
      confidence: r.score,
    }))
  } catch (error) {
    console.error('On-device AI error:', error)
    throw new Error(`Text generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

export async function summarizeText(text: string, maxLength: number = 100): Promise<string> {
  try {
    await initializeOnDeviceAI()
    const summarizer = await pipeline('summarization', 'Xenova/distilbart-cnn-6-6', {
      dtype: 'q4',
    })
    const results = await summarizer(text, {
      max_length: maxLength,
      min_length: 10,
    })
    return results[0]?.summary_text || ''
  } catch (error) {
    console.error('Summarization error:', error)
    throw new Error(`Summarization failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}
