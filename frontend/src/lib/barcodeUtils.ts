import JsBarcode from 'jsbarcode'

export function generateBarcode(text: string, canvas: HTMLCanvasElement): void {
  JsBarcode(canvas, text, { format: 'CODE128', width: 2, height: 80 })
}
