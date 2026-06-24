import { toCanvas } from 'qrcode'

export async function generateQRCode(text: string, canvas: HTMLCanvasElement): Promise<void> {
  await toCanvas(canvas, text, { width: 200, margin: 2 })
}
