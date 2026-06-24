import { describe, it, expect, vi } from 'vitest'
import { generateQRCode } from '../lib/qrcodeUtils'

vi.mock('qrcode', () => ({
  toCanvas: vi.fn().mockResolvedValue(undefined),
}))

describe('QR Code', () => {
  it('generates QR code on canvas', async () => {
    const canvas = document.createElement('canvas')
    await generateQRCode('test', canvas)
    const { toCanvas } = await import('qrcode') as any
    expect(vi.mocked(toCanvas)).toHaveBeenCalled()
  })
})
