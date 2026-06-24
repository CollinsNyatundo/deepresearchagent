import React, { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter'
import tsx from 'react-syntax-highlighter/dist/esm/languages/prism/tsx'
import typescript from 'react-syntax-highlighter/dist/esm/languages/prism/typescript'
import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript'
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python'
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash'
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json'
import yaml from 'react-syntax-highlighter/dist/esm/languages/prism/yaml'
import markdown from 'react-syntax-highlighter/dist/esm/languages/prism/markdown'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { exportElementToImage } from '../../lib/exportImage'
import { exportToPdf, exportToZip } from '../../lib/exportPdfZip'
import { Image, FileImage, FileText, FileArchive } from 'lucide-react'

SyntaxHighlighter.registerLanguage('tsx', tsx)
SyntaxHighlighter.registerLanguage('typescript', typescript)
SyntaxHighlighter.registerLanguage('javascript', javascript)
SyntaxHighlighter.registerLanguage('python', python)
SyntaxHighlighter.registerLanguage('bash', bash)
SyntaxHighlighter.registerLanguage('json', json)
SyntaxHighlighter.registerLanguage('yaml', yaml)
SyntaxHighlighter.registerLanguage('markdown', markdown)
SyntaxHighlighter.registerLanguage('md', markdown)

function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    import('mermaid').then((mermaid) => {
      if (cancelled) return
      mermaid.default.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'strict',
      })
      if (ref.current) {
        mermaid.default.render('mermaid-' + Math.random().toString(36).slice(2), chart)
          .then(({ svg }) => {
            if (ref.current && !cancelled) {
              ref.current.innerHTML = svg
            }
          })
          .catch((err) => {
            if (!cancelled) setError(String(err))
          })
      }
    })
    return () => { cancelled = true }
  }, [chart])

  if (error) {
    return <div className="text-[#c45a5a] text-xs p-2">Mermaid error: {error}</div>
  }

  return <div ref={ref} className="mermaid flex justify-center py-2" />
}

interface WikiLinkProps {
  href: string
  children: React.ReactNode
  onNavigate: (type: string, target: string) => void
}

export function WikiLinkRenderer({ href, children, onNavigate }: WikiLinkProps) {
  if (href.startsWith('wiki:') || href.startsWith('run:') || href.startsWith('doc:') || href.startsWith('entity:')) {
    const parts = href.split(':')
    const type = parts[0]
    const target = parts.slice(1).join(':')
    return (
      <span
        className="wiki-link"
        onClick={(e) => {
          e.preventDefault()
          onNavigate(type, target)
        }}
      >
        {children}
      </span>
    )
  }
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="wiki-link">
      {children}
    </a>
  )
}

interface MarkdownPreviewProps {
  content: string
  onNavigate: (type: string, target: string) => void
  showExport?: boolean
  exportFilename?: string
}

export function MarkdownPreview({ content, onNavigate, showExport = true, exportFilename = 'note' }: MarkdownPreviewProps) {
  const contentRef = useRef<HTMLDivElement>(null)
  const processed = content.replace(
    /\[\[([^\]]+)\]\]/g,
    (_match, inner) => `[${inner}](${inner.includes(':') ? inner : 'wiki:' + inner})`
  )

  const handleImageExport = async (format: 'png' | 'svg') => {
    if (contentRef.current) {
      await exportElementToImage(contentRef.current, format, exportFilename)
    }
  }

  const handlePdfExport = async () => {
    if (contentRef.current) {
      await exportToPdf(contentRef.current, exportFilename)
    }
  }

  const handleZipExport = async () => {
    const files = [
      { name: `${exportFilename}.md`, content: processed },
      { name: `${exportFilename}.html`, content: `<html><body>${processed}</body></html>` },
    ]
    await exportToZip(files, exportFilename)
  }

  return (
    <div className="relative">
      {showExport && (
        <div className="flex gap-2 mb-2 justify-end">
          <button
            onClick={() => handleImageExport('png')}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-[#1a1a2e]/60 border border-[rgba(255,255,255,0.06)] text-[#c4c6d8] hover:bg-[#1a1a2e]/90 transition-colors"
            title="Export as PNG"
          >
            <Image size={14} />
            PNG
          </button>
          <button
            onClick={() => handleImageExport('svg')}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-[#1a1a2e]/60 border border-[rgba(255,255,255,0.06)] text-[#c4c6d8] hover:bg-[#1a1a2e]/90 transition-colors"
            title="Export as SVG"
          >
            <FileImage size={14} />
            SVG
          </button>
          <button
            onClick={handlePdfExport}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-[#1a1a2e]/60 border border-[rgba(255,255,255,0.06)] text-[#c4c6d8] hover:bg-[#1a1a2e]/90 transition-colors"
            title="Export as PDF"
          >
            <FileText size={14} />
            PDF
          </button>
          <button
            onClick={handleZipExport}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-[#1a1a2e]/60 border border-[rgba(255,255,255,0.06)] text-[#c4c6d8] hover:bg-[#1a1a2e]/90 transition-colors"
            title="Export as ZIP"
          >
            <FileArchive size={14} />
            ZIP
          </button>
        </div>
      )}
      <div ref={contentRef} className="md-body">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ href, children }) => (
              <WikiLinkRenderer href={href || ''} onNavigate={onNavigate}>
                {children}
              </WikiLinkRenderer>
            ),
            code: ({ className, children }) => {
              const match = /language-(\w+)/.exec(className || '')
              const lang = match ? match[1] : ''
              if (lang === 'mermaid') {
                return <MermaidDiagram chart={String(children).replace(/\n$/, '')} />
              }
              return lang ? (
                <SyntaxHighlighter
                  style={oneDark as any}
                  language={lang}
                  PreTag="div"
                  className="rounded-lg text-sm"
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className}>
                  {children}
                </code>
              )
            },
          }}
        >
          {processed}
        </ReactMarkdown>
      </div>
    </div>
  )
}
