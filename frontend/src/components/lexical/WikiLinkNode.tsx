import {
  DecoratorNode,
  DOMConversionMap,
  DOMConversionOutput,
  NodeKey,
  SerializedLexicalNode,
  Spread,
} from 'lexical'
import { ReactNode } from 'react'

export type SerializedWikiLinkNode = Spread<
  {
    linkText: string
  },
  SerializedLexicalNode
>

export class WikiLinkNode extends DecoratorNode<ReactNode> {
  __linkText: string

  static getType(): string {
    return 'wiki-link'
  }

  static clone(node: WikiLinkNode): WikiLinkNode {
    return new WikiLinkNode(node.__linkText, node.__key)
  }

  static importJSON(serializedNode: SerializedWikiLinkNode): WikiLinkNode {
    const node = new WikiLinkNode(serializedNode.linkText)
    return node
  }

  constructor(linkText: string, key?: NodeKey) {
    super(key)
    this.__linkText = linkText
  }

  getLinkText(): string {
    return this.__linkText
  }

  createDOM(): HTMLElement {
    const span = document.createElement('span')
    span.className = 'wiki-link-node'
    span.textContent = `[[${this.__linkText}]]`
    return span
  }

  updateDOM(): false {
    return false
  }

  decorate(): ReactNode {
    return (
      <span className="wiki-link-node cursor-pointer text-[#3a7bd5] hover:underline">
        [[{this.__linkText}]]
      </span>
    )
  }

  exportJSON(): SerializedWikiLinkNode {
    return {
      ...super.exportJSON(),
      type: 'wiki-link',
      linkText: this.__linkText,
    }
  }

  static importDOM(): DOMConversionMap | null {
    return {
      span: (domNode: HTMLElement) => {
        if (domNode.className === 'wiki-link-node') {
          return {
            conversion: (): DOMConversionOutput => {
              const text = domNode.textContent?.replace(/^\[\[|\]\]$/g, '') || ''
              return { node: new WikiLinkNode(text) }
            },
            priority: 1,
          }
        }
        return null
      },
    }
  }
}

export function $createWikiLinkNode(linkText: string): WikiLinkNode {
  return new WikiLinkNode(linkText)
}

export function $isWikiLinkNode(node: any): node is WikiLinkNode {
  return node instanceof WikiLinkNode
}
