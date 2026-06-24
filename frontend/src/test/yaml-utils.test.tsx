import { describe, it, expect } from 'vitest'
import { parseYaml, toYaml, isValidYaml } from '../lib/yamlUtils'

describe('YAML Utils', () => {
  it('parses YAML to object', () => {
    const result = parseYaml('name: test\nvalue: 42')
    expect(result).toEqual({ name: 'test', value: 42 })
  })

  it('converts object to YAML', () => {
    const result = toYaml({ name: 'test' })
    expect(result).toContain('name: test')
  })

  it('validates correct YAML', () => {
    expect(isValidYaml('key: value')).toBe(true)
    expect(isValidYaml('{{{')).toBe(false)
  })
})
