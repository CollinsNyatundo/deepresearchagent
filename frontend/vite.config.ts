import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/mermaid')) return 'mermaid'
          if (id.includes('node_modules/recharts')) return 'recharts'
          if (id.includes('node_modules/framer-motion')) return 'framer-motion'
          if (id.includes('node_modules/pdfjs-dist') || id.includes('node_modules/pdf-lib')) return 'pdfjs'
          if (id.includes('node_modules/@huggingface/transformers') || id.includes('node_modules/tesseract.js')) return 'ai'
          if (id.includes('node_modules/react-syntax-highlighter')) return 'syntax'
          if (id.includes('node_modules/lexical') || id.includes('node_modules/@lexical')) return 'lexical'
          return null
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    exclude: ['@huggingface/transformers'],
  },
})
