import { describe, it, expect, vi } from 'vitest'
import { generateBarcode } from '../lib/barcodeUtils'

vi.mock('jsbarcode', () => ({
  default: vi.fn(),
}))

describe('Barcode', () => {
  it('generates barcode on canvas', () => {
    const canvas = document.createElement('canvas')
    expect(() => generateBarcode('12345', canvas)).not.toThrow()
  })
})
