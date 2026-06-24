import { createWorker } from 'tesseract.js'
import { toast } from 'sonner'

export interface OcrResult {
  text: string
  confidence: number
}

export async function extractTextFromImage(imageUrl: string | Blob): Promise<OcrResult> {
  try {
    const worker = await createWorker('eng')
    const result = await worker.recognize(imageUrl)
    await worker.terminate()

    return {
      text: result.data.text,
      confidence: result.data.confidence,
    }
  } catch (error) {
    toast.error(`OCR failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    throw error
  }
}
