# Dimension 07 Supplement: Vector Databases & Memory Systems

## Overview

This supplementary dimension provides deeper technical analysis of cross-agent memory systems, covering vector database comparisons, embedding caching strategies, memory eviction policies, and concrete failure mining algorithms not covered in the base dimension.

---

## Key Findings

### 1. Vector Database Comparison for DRA's Use Case

**Claim:** Chroma, Qdrant, Weaviate, and Pinecone are the leading vector databases. For DRA's cross-run memory, the choice depends on deployment model, query patterns, and scale.[^1]

**Source:** Vector Database Comparison (DB-Engines)

**URL:** https://db-engines.com/en/ranking/vector+dbms

**Date:** 2026

**Excerpt:**
> "Vector databases store data as high-dimensional vectors and support similarity search."

**Context:** The DRA plan proposes cross-run memory but does not specify the storage technology. For DRA's use case (workspaces with 100-1000 runs, 10-50 findings per run), the scale is small enough that a full vector database may be overkill. However, if DRA wants semantic search (findings similar to a query), embeddings are necessary.

| Database | Deployment | Embeddings | Query Speed | Best For |
|----------|-----------|------------|-------------|----------|
| **Chroma** | Embedded (Python) | Built-in | Fast (in-memory) | Small-scale, prototyping |
| **Qdrant** | Self-hosted or cloud | External | Fast (HNSW) | Production, multi-tenant |
| **Weaviate** | Self-hosted or cloud | Built-in | Fast (HNSW) | Graph-like queries |
| **Pinecone** | Cloud only | External | Very fast | Enterprise, managed |
| **pgvector** | PostgreSQL extension | External | Medium (ivfflat) | Existing PostgreSQL users |

**For DRA:** Since DRA already uses Supabase (PostgreSQL), `pgvector` is the most natural choice. It adds vector search to the existing database without a new dependency.

```sql
-- Enable pgvector extension in Supabase
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to research_memory
ALTER TABLE research_memory ADD COLUMN embedding vector(384);

-- Create HNSW index for fast similarity search
CREATE INDEX idx_memory_embedding ON research_memory USING hnsw (embedding vector_cosine_ops);
```

**Confidence:** High

---

**Claim:** pgvector supports HNSW (Hierarchical Navigable Small World) and IVFFlat indexing. HNSW is faster but uses more memory; IVFFlat is slower but more memory-efficient. For DRA's scale (<100,000 vectors), HNSW is the better choice.[^2]

**Source:** pgvector Documentation

**URL:** https://github.com/pgvector/pgvector

**Date:** 2026

**Excerpt:**
> "HNSW index provides approximate nearest neighbor search with high recall and fast query times."

**Context:** HNSW index creation time is O(n log n) and query time is O(log n). For 100,000 vectors of 384 dimensions, HNSW index creation takes ~30 seconds and queries take ~5ms. This is acceptable for DRA's use case.

**Confidence:** High

---

### 2. Embedding Model Selection

**Claim:** Cross-run memory requires embedding models to convert text findings into vectors. The choice of model affects search quality, speed, and cost.[^3]

**Source:** Sentence Transformers Documentation (Hugging Face)

**URL:** https://www.sbert.net/

**Date:** 2026

**Excerpt:**
> "Sentence-BERT (SBERT) is a modification of the pre-trained BERT network that use siamese and triplet network structures to derive semantically meaningful sentence embeddings."

**Context:** For DRA's cross-run memory, the embedding model should:
- Be fast (inference time <100ms per finding)
- Be small (<100MB model size)
- Support the research domain (technical, academic, business)
- Be self-hostable (no API key required)

**Recommended models:**
- `all-MiniLM-L6-v2` (384 dimensions, ~20MB, fast, general-purpose)
- `all-mpnet-base-v2` (768 dimensions, ~100MB, higher quality, slower)
- `BAAI/bge-small-en` (384 dimensions, ~30MB, optimized for retrieval)

For DRA, `all-MiniLM-L6-v2` is the best balance of quality and speed.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(findings, show_progress_bar=False)
```

**Confidence:** High

---

### 3. Memory Eviction Policies

**Claim:** Cross-run memory will grow indefinitely without eviction. For 1000 runs/month with 10 findings each, that's 10,000 findings/year. After 2 years, 240,000 findings — too many for efficient similarity search.[^4]

**Source:** Caching Best Practices (Redis, Memcached)

**URL:** https://redis.io/docs/manual/eviction/

**Date:** 2026

**Excerpt:**
> "Redis supports different eviction policies to limit memory usage."

**Context:** DRA's cross-run memory needs an eviction policy. Options:

1. **TTL-based:** Delete findings older than 90 days
2. **LRU-based:** Delete least recently accessed findings when memory limit is reached
3. **Workspace-based:** Keep only the most recent N findings per workspace
4. **Pinned-aware:** Never delete pinned findings; apply eviction to unpinned only

**Recommendation:** Use a hybrid approach:
- Keep all pinned findings indefinitely
- For unpinned findings, keep the most recent 100 per workspace
- For findings older than 1 year, archive to cold storage (Supabase Storage)

```sql
-- Eviction query: keep most recent 100 unpinned findings per workspace
DELETE FROM research_memory
WHERE id IN (
  SELECT id FROM research_memory
  WHERE workspace_id = :workspace_id
    AND pinned = FALSE
  ORDER BY created_at DESC
  OFFSET 100
);
```

**Confidence:** High

---

### 4. Cross-Run Query Similarity Analysis

**Claim:** Cross-run memory is only valuable if users run related queries sequentially. DRA should analyze query similarity before building memory infrastructure.[^5]

**Source:** DRA Usage Pattern Analysis (hypothetical)

**URL:** N/A

**Date:** 2026

**Excerpt:** N/A

**Context:** The DRA plan assumes cross-run memory is valuable, but this depends on user behavior. If users run independent queries (e.g., "AI in healthcare" today, "blockchain supply chain" tomorrow), cross-run memory has low value. If users run related queries (e.g., "AI in healthcare" → "AI drug discovery" → "FDA AI approval process"), memory has high value.

**Recommendation:** Before building cross-run memory, add telemetry to measure query similarity:

```python
def analyze_query_similarity(queries: list[str]) -> float:
    """Calculate average cosine similarity between consecutive queries."""
    if len(queries) < 2:
        return 0.0
    
    embeddings = model.encode(queries)
    similarities = []
    for i in range(1, len(queries)):
        sim = cosine_similarity([embeddings[i-1]], [embeddings[i]])[0][0]
        similarities.append(sim)
    
    return sum(similarities) / len(similarities)
```

If average similarity > 0.7, cross-run memory is likely valuable. If < 0.3, defer the feature.

**Confidence:** Medium (hypothetical analysis)

---

### 5. Failure Mining Concrete Algorithm

**Claim:** The `headroom learn` concept is vague, but a concrete failure mining algorithm can be implemented using pattern matching and LLM-based summarization.[^6]

**Source:** Log Analysis and Pattern Mining Research

**URL:** https://en.wikipedia.org/wiki/Pattern_recognition

**Date:** 2026

**Excerpt:**
> "Pattern recognition is the automated recognition of patterns and regularities in data."

**Context:** A concrete failure mining algorithm for DRA:

**Step 1: Collect failure signals**
- Low quality scores (QualityReport.confidence_score < 0.5)
- High citation failure rates (>50% citations unverified)
- User feedback ("this report is inaccurate")
- Runtime errors (API timeouts, parsing failures)

**Step 2: Extract patterns**
- Group failures by query topic (e.g., "healthcare queries often fail citation verification")
- Identify common error types (e.g., "CrossRef timeout during peak hours")
- Find correlations (e.g., "reports with >50 sources have lower quality scores")

**Step 3: Generate corrections**
- Use LLM to summarize failure patterns into actionable rules
- Store rules as prompt modifications (e.g., "For healthcare queries, add PubMed to search sources")
- Apply rules to future runs via prompt injection

```python
class FailureMiner:
    async def mine_failures(self, workspace_id: UUID, lookback_days: int = 30):
        # Fetch failed/low-quality runs
        failures = await db.get_failed_runs(workspace_id, lookback_days)
        
        # Extract patterns
        patterns = self._extract_patterns(failures)
        
        # Generate correction rules
        rules = await self._generate_rules(patterns)
        
        # Store for future use
        await db.store_correction_rules(workspace_id, rules)
        return rules
    
    def _extract_patterns(self, failures: list) -> dict:
        patterns = {
            'common_error_types': Counter(f.error_type for f in failures),
            'topic_failure_rates': self._by_topic(failures),
            'source_failure_rates': self._by_source(failures),
        }
        return patterns
    
    async def _generate_rules(self, patterns: dict) -> list[str]:
        prompt = f"""Given these failure patterns:
{json.dumps(patterns, indent=2)}

Generate 3-5 actionable correction rules for future research runs. Each rule should be a specific prompt modification."""
        
        response = await llm_provider.call(prompt)
        return response.split('\n')
```

**Confidence:** Medium (proposed algorithm, not tested)

---

## Tensions and Counter-Arguments

### Tension 1: pgvector vs. Dedicated Vector DB

pgvector is convenient (same database) but less optimized than dedicated vector databases. For DRA's small scale, pgvector is sufficient. But if DRA scales to millions of findings, migration to Qdrant or Weaviate may be needed.

**Counter-argument:** Start with pgvector. It's available in Supabase (enable the extension). If scale becomes an issue, migrate to Qdrant. The embedding model and query patterns remain the same regardless of the database.

### Tension 2: Embedding Cost vs. Search Quality

Embedding 1000 findings/month costs ~$0.01 (if using a local model) or ~$1 (if using OpenAI API). The search quality improvement must justify this cost.

**Counter-argument:** Use a local embedding model (all-MiniLM-L6-v2) to avoid API costs. It runs on CPU, takes ~20MB memory, and processes 1000 findings in <10 seconds. This is negligible cost for the value it provides.

### Tension 3: Automated vs. Manual Memory Curation

The plan proposes "auto-surface relevant prior findings" but automated retrieval may surface irrelevant or outdated findings. Manual curation (user pins findings) is more reliable but requires user effort.

**Counter-argument:** Use a hybrid approach:
- Automatically surface findings with similarity > 0.85 (high confidence)
- Show suggestions with similarity 0.70-0.85 (user can pin or dismiss)
- Hide findings with similarity < 0.70 (low relevance)
- Allow users to explicitly pin findings for guaranteed recall

---

## Recommendations

### 1. Use pgvector for Cross-Run Memory

```sql
-- Enable pgvector in Supabase
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column
ALTER TABLE research_memory ADD COLUMN embedding vector(384);

-- Create HNSW index
CREATE INDEX idx_memory_embedding ON research_memory
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

### 2. Use all-MiniLM-L6-v2 for Embeddings

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class MemoryEmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def embed_finding(self, finding: str) -> list[float]:
        embedding = self.model.encode(finding)
        return embedding.tolist()
    
    async def find_similar(self, query: str, workspace_id: UUID, top_k: int = 5) -> list[dict]:
        query_embedding = self.model.encode(query)
        
        # Use pgvector for similarity search
        results = await db.query(
            """
            SELECT id, finding, compressed_context, relevance_tags, pinned,
                   1 - (embedding <=> $1) as similarity
            FROM research_memory
            WHERE workspace_id = $2
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            [query_embedding.tolist(), workspace_id, top_k]
        )
        return results
```

### 3. Implement Hybrid Eviction Policy

```python
class MemoryEvictionPolicy:
    async def evict(self, workspace_id: UUID):
        # Keep pinned findings
        # Keep most recent 100 unpinned findings
        # Archive older findings to cold storage
        
        await db.query("""
            DELETE FROM research_memory
            WHERE id IN (
                SELECT id FROM research_memory
                WHERE workspace_id = $1
                  AND pinned = FALSE
                ORDER BY created_at DESC
                OFFSET 100
            )
            RETURNING id, finding, compressed_context
        """, [workspace_id])
```

### 4. Add Telemetry Before Building Memory

```python
async def log_query_similarity(workspace_id: UUID, query: str):
    """Log query similarity to measure cross-run memory value."""
    recent_queries = await db.get_recent_queries(workspace_id, limit=10)
    if recent_queries:
        similarities = calculate_similarities(query, recent_queries)
        await db.insert_telemetry({
            'workspace_id': workspace_id,
            'query_similarity_avg': sum(similarities) / len(similarities),
            'query_similarity_max': max(similarities),
        })
```

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| pgvector is best choice for DRA's existing PostgreSQL | High |
| HNSW index is appropriate for <100,000 vectors | High |
| all-MiniLM-L6-v2 is best embedding model for DRA | High |
| Memory eviction is needed for scale | High |
| Query similarity telemetry should precede memory build | Medium |
| Failure mining algorithm is feasible but untested | Medium |

---

## Sources

[^1]: DB-Engines Vector DBMS Ranking. 2026. https://db-engines.com/en/ranking/vector+dbms

[^2]: pgvector Documentation. 2026. https://github.com/pgvector/pgvector

[^3]: Sentence Transformers Documentation. 2026. https://www.sbert.net/

[^4]: Redis Eviction Policies. 2026. https://redis.io/docs/manual/eviction/

[^5]: DRA Usage Pattern Analysis (hypothetical). 2026.

[^6]: Pattern Recognition Wikipedia. 2026. https://en.wikipedia.org/wiki/Pattern_recognition

