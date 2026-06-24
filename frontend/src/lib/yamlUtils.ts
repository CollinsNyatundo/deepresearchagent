import { load, dump } from 'js-yaml'

export function parseYaml(text: string): unknown {
  return load(text)
}

export function toYaml(obj: unknown): string {
  return dump(obj)
}

export function isValidYaml(text: string): boolean {
  try {
    load(text)
    return true
  } catch {
    return false
  }
}
