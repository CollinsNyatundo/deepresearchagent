export const siteConfig = {
  title: 'Deep Research Agent',
  description: 'AI-powered deep research conductor',
  language: 'en',
}

export const headerConfig = {
  brandMark: '◊',
  brandName: 'DeepResearch',
  brandSuffix: '.ai',
}

export const backgroundConfig = {
  modes: [
    { value: 'moonlit' as const, label: 'Moonlit Ripple', icon: '◐' },
    { value: 'silk' as const, label: 'Silk Flow Field', icon: '◑' },
    { value: 'rain' as const, label: 'Rain on Glass', icon: '◒' },
    { value: 'solid' as const, label: 'Solid Color', icon: '◓' },
  ],
  solidColors: [
    { value: '#000000' as const, label: 'Ink Black' },
    { value: '#1a1a2e' as const, label: 'Deep Blue' },
    { value: '#1a1308' as const, label: 'Brown' },
    { value: '#0d1f0d' as const, label: 'Dark Green' },
  ],
}

export const sidebarConfig = {
  searchPlaceholder: 'Search notes...',
  newNoteLabel: '+ New Note',
  manageLabel: 'Manage',
  cancelLabel: 'Cancel',
  deleteLabel: 'Delete',
  selectAllLabel: 'Select All',
}

export const editorConfig = {
  editTab: 'Edit',
  previewTab: 'Preview',
  titlePlaceholder: 'Note title',
  contentPlaceholder: 'Start writing...',
  outgoingLinksLabel: 'Outgoing Links',
  backlinksLabel: 'Backlinks',
  sourceLabel: 'Source',
  autoSaveDelay: 400,
}

export const graphConfig = {
  nodesLabel: 'nodes',
  edgesLabel: 'edges',
}

export const moonConfig = {
  phaseLabels: [
    'New Moon',
    'Waxing Crescent',
    'First Quarter',
    'Waxing Gibbous',
    'Full Moon',
    'Waning Gibbous',
    'Last Quarter',
    'Waning Crescent',
  ],
}

export const appConfig = {
  emptyState: 'Select a note to begin',
  loadingState: 'Loading...',
  signOutLabel: 'Sign Out',
  loginPrompt: 'Please sign in to continue',
  loginButton: 'Sign In',
}

export const starterNotes = [
  {
    title: 'Overview of Large Language Models',
    content: `# Overview of Large Language Models

Large Language Models (LLMs) are a type of artificial intelligence model trained on vast amounts of text data to understand and generate human language.

## Key Concepts

- **[[Transformer Architecture]]**: The foundational architecture behind modern LLMs
- **[[Attention Mechanism]]**: How models focus on relevant parts of input
- **[[Pre-training & Fine-tuning]]**: The two-stage training process

## Applications

LLMs power applications ranging from chatbots to code generation.`,
    tags: ['llm', 'overview'],
  },
  {
    title: 'Transformer Architecture',
    content: `# Transformer Architecture

The Transformer architecture, introduced in "Attention Is All You Need" (2017), revolutionized NLP.

## Components

- **Self-attention**: Allows tokens to attend to each other
- **Multi-head attention**: Parallel attention mechanisms
- **Feed-forward networks**: Position-wise transformations
- **Positional encoding**: Injects sequence position information

## Related Concepts

See [[Attention Mechanism]] for details on how attention works.`,
    tags: ['transformer', 'architecture'],
  },
  {
    title: 'Attention Mechanism',
    content: `# Attention Mechanism

Attention allows models to focus on relevant parts of the input sequence when producing each element of the output.

## Types

- **Self-attention**: Tokens attend to themselves
- **Cross-attention**: Query from one sequence attends to keys from another
- **Multi-head attention**: Multiple parallel attention heads

## Related

Part of the [[Transformer Architecture]].`,
    tags: ['attention', 'transformer'],
  },
  {
    title: 'Pre-training & Fine-tuning',
    content: `# Pre-training & Fine-tuning

LLMs are trained in two stages: pre-training on large corpora, then fine-tuning on specific tasks.

## Pre-training Objectives

- **Masked language modeling**: Predicting masked tokens
- **Causal language modeling**: Predicting next token
- **Prefix LM**: Predicting continuation given prefix

## Fine-tuning Methods

- **Full fine-tuning**: Updating all parameters
- **LoRA**: Low-rank adaptation
- **Prompt tuning**: Learning soft prompts

## Related

See [[Transformer Architecture]] and [[Attention Mechanism]].`,
    tags: ['training', 'fine-tuning'],
  },
  {
    title: 'Prompt Engineering',
    content: `# Prompt Engineering

The art of crafting effective inputs to LLMs to elicit desired outputs.

## Techniques

- **Chain-of-thought**: Encourage step-by-step reasoning
- **Few-shot prompting**: Provide examples in the prompt
- **Zero-shot prompting**: Direct instruction without examples
- **System prompts**: Set behavioral context

## Related

Used with [[Pre-training & Fine-tuning]] models.`,
    tags: ['prompting', 'engineering'],
  },
  {
    title: 'Retrieval-Augmented Generation',
    content: `# Retrieval-Augmented Generation (RAG)

RAG combines LLMs with external knowledge retrieval to ground generation in factual information.

## Architecture

- **Retriever**: Finds relevant documents from a corpus
- **Generator**: Produces output conditioned on retrieved context

## Benefits

- Reduces hallucination
- Provides source attribution
- Enables dynamic knowledge updates

## Related

See [[Prompt Engineering]] for how prompts are crafted with retrieved context.`,
    tags: ['rag', 'retrieval'],
  },
  {
    title: 'Model Evaluation',
    content: `# Model Evaluation

Evaluating LLMs requires diverse benchmarks covering reasoning, knowledge, and safety.

## Benchmarks

- **MMLU**: Multi-task language understanding
- **HellaSwag**: Commonsense reasoning
- **HumanEval**: Code generation
- **MT-Bench**: Multi-turn conversation

## Metrics

- Perplexity, BLEU, ROUGE for generation
- Accuracy for classification

## Related

Evaluation informs [[AI Safety & Alignment]] decisions.`,
    tags: ['evaluation', 'benchmarks'],
  },
  {
    title: 'AI Safety & Alignment',
    content: `# AI Safety & Alignment

Ensuring LLMs behave in accordance with human values and intentions.

## Key Areas

- **RLHF**: Reinforcement Learning from Human Feedback
- **Constitutional AI**: Self-critique and revision
- **Red teaming**: Adversarial testing
- **Interpretability**: Understanding model internals

## Related

See [[Model Evaluation]] for safety benchmarks.`,
    tags: ['safety', 'alignment'],
  },
  {
    title: 'Generative AI Applications',
    content: `# Generative AI Applications

LLMs enable a wide range of creative and practical applications.

## Applications

- **Content generation**: Articles, stories, marketing copy
- **Code generation**: Programming assistants, code completion
- **Translation**: Cross-lingual communication
- **Summarization**: Condensing long documents

## Related

Built on [[Transformer Architecture]] and [[Pre-training & Fine-tuning]].`,
    tags: ['applications', 'generation'],
  },
  {
    title: 'Multimodal Models',
    content: `# Multimodal Models

Models that process and generate multiple modalities: text, images, audio, video.

## Examples

- **Vision-language models**: Understanding images with text
- **Speech-to-text**: Audio transcription
- **Text-to-image**: Generating images from descriptions

## Architecture

Extends [[Transformer Architecture]] with modality-specific encoders/decoders.`,
    tags: ['multimodal', 'vision'],
  },
  {
    title: 'Deep Learning Fundamentals',
    content: `# Deep Learning Fundamentals

The mathematical foundations powering modern AI.

## Concepts

- **Neural networks**: Layers of parameterized functions
- **Backpropagation**: Gradient-based optimization
- **Activation functions**: Introducing non-linearity
- **Regularization**: Preventing overfitting

## Related

These fundamentals enable [[Transformer Architecture]] and [[Attention Mechanism]].`,
    tags: ['deep-learning', 'fundamentals'],
  },
  {
    title: 'Reasoning & Long Context',
    content: `# Reasoning & Long Context

Extending LLM capabilities to complex reasoning and long document understanding.

## Techniques

- **Chain-of-thought prompting**: Step-by-step reasoning
- **Tree of Thoughts**: Exploring multiple reasoning paths
- **Long-context models**: Processing 100k+ tokens
- **Memory mechanisms**: External memory for long contexts

## Related

See [[Prompt Engineering]] and [[Attention Mechanism]].`,
    tags: ['reasoning', 'context'],
  },
]
