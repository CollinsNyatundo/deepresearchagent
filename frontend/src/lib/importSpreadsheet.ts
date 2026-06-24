import Papa from 'papaparse'
import * as XLSX from 'xlsx'
import { toast } from 'sonner'

export interface ParsedData {
  headers: string[]
  rows: Record<string, string | number | boolean | null>[]
  raw: string[][]
}

export function parseCsv(file: File): Promise<ParsedData> {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const headers = results.meta.fields || []
        resolve({
          headers,
          rows: results.data as Record<string, string | number | boolean | null>[],
          raw: results.data as string[][],
        })
      },
      error: (error) => {
        toast.error(`CSV parse error: ${error.message}`)
        reject(error)
      },
    })
  })
}

export function parseExcel(file: File): Promise<ParsedData> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer)
        const workbook = XLSX.read(data, { type: 'array' })
        const firstSheet = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheet]
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as string[][]
        
        if (jsonData.length === 0) {
          resolve({ headers: [], rows: [], raw: [] })
          return
        }
        
        const headers = jsonData[0]
        const rows = jsonData.slice(1).map((row) => {
          const obj: Record<string, string | number | boolean | null> = {}
          headers.forEach((header, index) => {
            obj[header] = row[index] ?? null
          })
          return obj
        })
        
        resolve({ headers, rows, raw: jsonData })
      } catch (error) {
        toast.error(`Excel parse error: ${error instanceof Error ? error.message : 'Unknown error'}`)
        reject(error)
      }
    }
    reader.onerror = () => {
      toast.error('Failed to read Excel file')
      reject(new Error('Failed to read Excel file'))
    }
    reader.readAsArrayBuffer(file)
  })
}

export async function parseSpreadsheet(file: File): Promise<ParsedData> {
  const extension = file.name.split('.').pop()?.toLowerCase()
  
  if (extension === 'csv') {
    return parseCsv(file)
  } else if (extension === 'xlsx' || extension === 'xls') {
    return parseExcel(file)
  }
  
  throw new Error(`Unsupported file format: ${extension}`)
}
