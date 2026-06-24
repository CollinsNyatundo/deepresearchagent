# TDD Implementation Plan — BrowseryTools Library Adoption

> **Methodology:** Test-Driven Development (vertical slices)  
> **Skill:** `test-driven-dev` — one test → one implementation → repeat  
> **Target:** All 5 phases from browsery-tools-analysis.md + PDF export backend  
> **Date:** 2026-06-22

---

## Phase 0: Test Infrastructure (Prerequisite)

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitejs/plugin-react
```

Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
})
```

Create `src/test/setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

Add to `package.json` scripts:
```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage"
```

---

## Phase 1: Foundation (HIGH Leverage)

### 1A. Sonner Toast Notifications
**Behavior to test:** "When user saves a note, a toast notification appears saying 'Note saved'"
```bash
npm install sonner
```

**Vertical slice:**
- RED: Test that `toast.success()` renders a visible toast with correct message
- GREEN: Install sonner, wrap app in `<Toaster>`, add `toast.success()` calls to save handlers
- REFACTOR: Extract toast patterns into reusable hooks

### 1B. Zod + React Hook Form Validation
**Behavior to test:** "When user submits an empty research query, an error message appears and no API call is made"
```bash
npm install zod react-hook-form @hookform/resolvers
```

**Vertical slices:**
1. QueryPanel validation (query length >= 3 chars)
2. NotesModule validation (title required)
3. SkillFactory validation (name and intent required)

### 1C. CmdK Command Palette
**Behavior to test:** "When user presses Ctrl+K, a command palette opens showing search results"
```bash
npm install cmdk
```

**Vertical slices:**
1. CmdK dialog opens on Ctrl+K
2. Search filters notes, runs, documents
3. Selecting a result navigates to the correct page

### 1D. React Syntax Highlighter
**Behavior to test:** "When MarkdownPreview renders a code block, syntax highlighting is applied"
```bash
npm install react-syntax-highlighter
npm install -D @types/react-syntax-highlighter
```

**Vertical slice:**
- RED: Test that code blocks have syntax highlighting classes
- GREEN: Replace default code renderer in MarkdownPreview with SyntaxHighlighter

---

## Phase 2: Content (HIGH Leverage)

### 2A. Lexical Rich Text Editor
**Behavior to test:** "When user types in the Notes editor, bold/italic formatting works and content saves as Markdown"
```bash
npm install lexical @lexical/react @lexical/markdown
```

**Vertical slices:**
1. Lexical editor renders in NotesModule
2. Basic formatting (bold, italic) works
3. Content serializes to Markdown on change
4. Markdown deserializes to Lexical on load
5. Wiki link detection ([[Title]])

### 2B. Mermaid Diagram Rendering
**Behavior to test:** "When MarkdownPreview encounters a Mermaid code block, it renders a diagram"
```bash
npm install mermaid
```

**Vertical slices:**
1. Mermaid code block detection in MarkdownPreview
2. Mermaid diagram renders in the DOM
3. Lazy loading of Mermaid library

### 2C. html-to-image Export
**Behavior to test:** "When user clicks 'Export as Image', the mindmap is downloaded as PNG"
```bash
npm install html-to-image
```

**Vertical slices:**
1. Export button in mindmap view
2. toPng converts DOM to image
3. Download triggers in browser

### 2D. PDF Preview + ZIP Export
**Behavior to test:** "When user clicks 'Export Bundle', a ZIP containing report and citations is downloaded"
```bash
npm install pdf-lib pdfjs-dist jszip
```

**Vertical slices:**
1. PDF preview for uploaded documents
2. ZIP creation with jszip
3. ZIP download trigger

---

## Phase 3: AI (HIGH Leverage)

### 3A. On-Device AI (Transformers.js)
**Behavior to test:** "When user exports a report, PII is detected and user is prompted to redact"
```bash
npm install @huggingface/transformers
```

**Vertical slices:**
1. PII detector loads and runs client-side
2. PII entities are identified in text
3. User can choose to redact or keep

### 3B. gpt-tokenizer
**Behavior to test:** "When user types a research query, token count is displayed in real-time"
```bash
npm install gpt-tokenizer
```

**Vertical slices:**
1. Token counter component in QueryPanel
2. Token count updates on every keystroke
3. Cost estimate calculated from token count

### 3C. tesseract.js OCR
**Behavior to test:** "When user uploads an image, text is extracted and displayed"
```bash
npm install tesseract.js
```

**Vertical slices:**
1. OCR button in Documents upload
2. tesseract.js loads language model
3. Text extracted from image
4. Extracted text can be added to OpenKB

---

## Phase 4: Data (MEDIUM Leverage)

### 4A. CSV/Excel Import
**Behavior to test:** "When user uploads a CSV, data is parsed and previewed as a table"
```bash
npm install papaparse xlsx
```

### 4B. Text Diff
**Behavior to test:** "When user compares two notes, differences are highlighted"
```bash
npm install diff
npm install -D @types/diff
```

### 4C. Cron Human-Readable Display
**Behavior to test:** "When cron expression is shown, human-readable text appears next to it"
```bash
npm install cron-parser cronstrue
```

### 4D. React Dropzone
**Behavior to test:** "When user drags a file over the upload area, it highlights and accepts the file"
```bash
npm install react-dropzone
```

---

## Phase 5: Polish (LOW-MEDIUM Leverage)

### 5A. Framer Motion
**Behavior to test:** "When page transitions, animation is smooth"
```bash
npm install framer-motion
```

### 5B. Recharts
**Behavior to test:** "When report contains data, a chart is rendered"
```bash
npm install recharts
```

### 5C. react-colorful
**Behavior to test:** "When user customizes mindmap, color picker appears"
```bash
npm install react-colorful
```

---

## Phase 6: PDF Export Backend (md-to-pdf skill)

**Behavior to test:** "When user clicks 'Export PDF', a PDF is generated from the markdown report and downloaded"

**Backend (TDD):**
```python
# RED: Test POST /research/{run_id}/export/pdf returns a PDF file
# GREEN: Implement endpoint using md-to-pdf skill or pdf-lib
```

**Frontend (TDD):**
```typescript
// RED: Test clicking 'Export PDF' triggers download
// GREEN: Add button to ReportView, call backend endpoint
```

---

## Vite Config Updates

```typescript
// vite.config.ts — add for lazy loading and WASM support
export default {
  optimizeDeps: {
    exclude: ['@huggingface/transformers', 'tesseract.js'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'ai-models': ['@huggingface/transformers'],
          'pdf': ['pdf-lib', 'pdfjs-dist'],
          'editor': ['lexical', '@lexical/react', '@lexical/markdown'],
          'mermaid': ['mermaid'],
          'charts': ['recharts'],
        },
      },
    },
  },
}
```

---

## TDD Checklist Per Slice

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
[ ] Build passes after implementation
[ ] Backend syntax verified (py_compile)
```

---

*End of TDD Implementation Plan. Execute vertical slices sequentially. Never refactor while RED.*
