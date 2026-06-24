import { describe, it, expect, vi } from 'vitest'
import { parseCsv, parseExcel } from '../lib/importSpreadsheet'

vi.mock('papaparse', () => ({
  default: {
    parse: vi.fn((_file, config) => {
      config.complete({
        data: [
          { name: 'Alice', age: '30' },
          { name: 'Bob', age: '25' },
        ],
        meta: { fields: ['name', 'age'] },
      })
    }),
  },
}))

vi.mock('xlsx', () => ({
  read: vi.fn().mockReturnValue({
    SheetNames: ['Sheet1'],
    Sheets: {
      Sheet1: {},
    },
  }),
  utils: {
    sheet_to_json: vi.fn().mockReturnValue([
      ['name', 'age'],
      ['Alice', '30'],
      ['Bob', '25'],
    ]),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('CSV/Excel Import', () => {
  it('parses CSV file correctly', async () => {
    const file = new File(['name,age\nAlice,30\nBob,25'], 'test.csv', { type: 'text/csv' })
    const result = await parseCsv(file)
    
    expect(result.headers).toEqual(['name', 'age'])
    expect(result.rows).toHaveLength(2)
    expect(result.rows[0]).toMatchObject({ name: 'Alice', age: '30' })
  })

  it('parses Excel file correctly', async () => {
    const file = new File([''], 'test.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const result = await parseExcel(file)
    
    expect(result.headers).toEqual(['name', 'age'])
    expect(result.rows).toHaveLength(2)
  })
})
