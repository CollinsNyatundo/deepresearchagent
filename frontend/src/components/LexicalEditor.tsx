import { useEffect } from 'react'
import { LexicalComposer } from '@lexical/react/LexicalComposer'
import { RichTextPlugin } from '@lexical/react/LexicalRichTextPlugin'
import { ContentEditable } from '@lexical/react/LexicalContentEditable'
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin'
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin'
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext'
import { MarkdownShortcutPlugin } from '@lexical/react/LexicalMarkdownShortcutPlugin'
import { $getRoot, EditorState, FORMAT_TEXT_COMMAND } from 'lexical'
import { $createHeadingNode, $createQuoteNode, HeadingNode, QuoteNode } from '@lexical/rich-text'
import { $convertFromMarkdownString, $convertToMarkdownString } from '@lexical/markdown'
import { TRANSFORMERS } from '@lexical/markdown'
import { Bold, Italic, Heading, Quote } from 'lucide-react'
import { WikiLinkNode } from './lexical/WikiLinkNode'

const theme = {
  paragraph: 'mb-2',
  h1: 'text-2xl font-bold mb-4',
  h2: 'text-xl font-bold mb-3',
  h3: 'text-lg font-bold mb-2',
  quote: 'border-l-4 border-[#3a7bd5] pl-4 italic mb-2',
  code: 'bg-[#1a1a2e] rounded p-2 font-mono text-sm',
  bold: 'font-bold',
  italic: 'italic',
  'wiki-link': 'wiki-link-node',
}

interface LexicalEditorProps {
  initialValue?: string
  onChange?: (markdown: string) => void
}

function EditorContent({ initialValue, onChange }: { initialValue?: string; onChange?: (markdown: string) => void }) {
  const [editor] = useLexicalComposerContext()

  useEffect(() => {
    if (initialValue) {
      editor.update(() => {
        const root = $getRoot()
        root.clear()
        $convertFromMarkdownString(initialValue, TRANSFORMERS)
      })
    }
  }, [editor, initialValue])

  const handleChange = (editorState: EditorState) => {
    editorState.read(() => {
      const markdown = $convertToMarkdownString(TRANSFORMERS)
      onChange?.(markdown)
    })
  }

  const formatBold = () => {
    editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'bold')
  }

  const formatItalic = () => {
    editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'italic')
  }

  const formatHeading = () => {
    editor.update(() => {
      const selection = $getRoot().selectEnd()
      const anchor = selection?.anchor
      if (anchor) {
        const node = anchor.getNode()
        const parent = node.getParent()
        if (parent) {
          const headingNode = $createHeadingNode('h2')
          headingNode.append(node)
          parent.append(headingNode)
        }
      }
    })
  }

  const formatQuote = () => {
    editor.update(() => {
      const selection = $getRoot().selectEnd()
      const anchor = selection?.anchor
      if (anchor) {
        const node = anchor.getNode()
        const parent = node.getParent()
        if (parent) {
          const quoteNode = $createQuoteNode()
          quoteNode.append(node)
          parent.append(quoteNode)
        }
      }
    })
  }

  return (
    <div>
      <div className="flex gap-2 mb-2">
        <button onClick={formatBold} className="p-1 rounded hover:bg-[rgba(255,255,255,0.1)]" title="Bold">
          <Bold size={16} />
        </button>
        <button onClick={formatItalic} className="p-1 rounded hover:bg-[rgba(255,255,255,0.1)]" title="Italic">
          <Italic size={16} />
        </button>
        <button onClick={formatHeading} className="p-1 rounded hover:bg-[rgba(255,255,255,0.1)]" title="Heading">
          <Heading size={16} />
        </button>
        <button onClick={formatQuote} className="p-1 rounded hover:bg-[rgba(255,255,255,0.1)]" title="Quote">
          <Quote size={16} />
        </button>
      </div>
      <OnChangePlugin onChange={handleChange} />
      <MarkdownShortcutPlugin transformers={TRANSFORMERS} />
      <RichTextPlugin
        contentEditable={
          <ContentEditable className="min-h-[200px] p-4 rounded-lg border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.02)] focus:outline-none focus:ring-2 focus:ring-[#3a7bd5]" />
        }
        placeholder={<div className="absolute top-16 left-4 text-[#c4c6d8]/40">Start typing...</div>}
        ErrorBoundary={({ children }) => <div>{children}</div>}
      />
      <HistoryPlugin />
    </div>
  )
}

export function LexicalEditor({ initialValue, onChange }: LexicalEditorProps) {
  const initialConfig = {
    namespace: 'DRAEditor',
    theme,
    onError: (error: Error) => {
      console.error('Lexical error:', error)
    },
    nodes: [HeadingNode, QuoteNode, WikiLinkNode],
  }

  return (
    <LexicalComposer initialConfig={initialConfig}>
      <EditorContent initialValue={initialValue} onChange={onChange} />
    </LexicalComposer>
  )
}
