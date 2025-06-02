# Dual Database Support for YouTube Transcripts

## Overview

YouTube Transcripts now supports both **SQLite** and **ArangoDB** backends, allowing it to function as:
1. **Standalone tool** with SQLite (no dependencies)
2. **Granger module** with ArangoDB (advanced features)

This matches the architecture needed for both YouTube Transcripts and ArXiv MCP Server.

## Quick Start

### Standalone Mode (SQLite)
```bash
# No configuration needed - SQLite is the default
youtube-transcripts search "machine learning"

# Or explicitly set SQLite
export YOUTUBE_DB_BACKEND=sqlite
youtube-transcripts search "transformers"
```

### Granger Integration Mode (ArangoDB)
```bash
# Configure ArangoDB
export YOUTUBE_DB_BACKEND=arangodb
export YOUTUBE_ARANGO_HOST=http://localhost:8529
export YOUTUBE_ARANGO_DATABASE=memory_bank

youtube-transcripts search "neural networks"
```

### Auto-Detection Mode
```bash
# Let the system decide based on availability
export YOUTUBE_DB_BACKEND=auto
youtube-transcripts search "deep learning"
```

## Architecture

```
┌─────────────────────────────────────┐
│         UnifiedSearchV2             │
│   (Main API - unchanged for users)  │
└─────────────────┬───────────────────┘
                  │
         ┌────────▼────────┐
         │ DatabaseAdapter │
         │ (Auto-selects)  │
         └────┬─────────┬──┘
              │         │
     ┌────────▼──┐ ┌───▼────────┐
     │  SQLite   │ │  ArangoDB  │
     │  Backend  │ │  Backend   │
     └───────────┘ └────────────┘
```

## Configuration

### Environment Variables
Create a `.env` file:

```bash
# Backend selection
YOUTUBE_DB_BACKEND=auto  # sqlite, arangodb, or auto

# SQLite settings (for standalone)
YOUTUBE_SQLITE_PATH=youtube_transcripts.db
YOUTUBE_SQLITE_JOURNAL_MODE=WAL
YOUTUBE_SQLITE_CACHE_SIZE=-64000

# ArangoDB settings (for Granger)
YOUTUBE_ARANGO_HOST=http://localhost:8529
YOUTUBE_ARANGO_DATABASE=memory_bank
YOUTUBE_ARANGO_USERNAME=root
YOUTUBE_ARANGO_PASSWORD=
YOUTUBE_ARANGO_PREFIX=youtube_
YOUTUBE_ARANGO_GRAPH=youtube_knowledge_graph

# Feature flags
YOUTUBE_ENABLE_EMBEDDINGS=true
YOUTUBE_ENABLE_GRAPH=true
YOUTUBE_ENABLE_RESEARCH=true
```

### Programmatic Configuration
```python
from youtube_transcripts.unified_search_v2 import UnifiedSearchV2

# Auto-detect backend
search = UnifiedSearchV2()

# Force SQLite
search = UnifiedSearchV2({'backend': 'sqlite'})

# Force ArangoDB
search = UnifiedSearchV2({
    'backend': 'arangodb',
    'arango_config': {
        'host': 'http://localhost:8529',
        'database': 'memory_bank'
    }
})

# Check which backend is active
print(search.backend_info)
```

## Feature Comparison

| Feature | SQLite | ArangoDB |
|---------|--------|----------|
| **Basic Search** | ✅ BM25 full-text | ✅ BM25 + Semantic |
| **Storage** | ✅ Simple & fast | ✅ Graph relationships |
| **Citations** | ✅ Store & retrieve | ✅ Citation networks |
| **Speakers** | ✅ Basic info | ✅ Speaker networks |
| **Evidence Finding** | ⚠️ Basic similarity | ✅ LLM-powered analysis |
| **Related Videos** | ⚠️ Same channel only | ✅ Graph traversal |
| **Embeddings** | ❌ Not supported | ✅ Vector search |
| **Knowledge Graph** | ❌ Not supported | ✅ Full graph DB |
| **Scalability** | ⚠️ Single file | ✅ Distributed |
| **Dependencies** | ✅ None (built-in) | ⚠️ Requires ArangoDB |

## Usage Examples

### 1. Basic Search (Works with Both)
```python
from youtube_transcripts.unified_search_v2 import UnifiedSearchV2

search = UnifiedSearchV2()
results = await search.search("machine learning")

print(f"Found {results['total_results']} results")
print(f"Using {results['backend']} backend")
```

### 2. Evidence Finding (Better with ArangoDB)
```python
# Find supporting/contradicting evidence
evidence = await search.find_evidence(
    claim="Transformers outperform RNNs",
    evidence_type="both"
)

# With SQLite: Basic text similarity
# With ArangoDB: LLM-powered analysis + graph context
```

### 3. Related Videos (Much better with ArangoDB)
```python
# Find related videos
related = await search.find_related("video_id", limit=10)

# With SQLite: Only same channel
# With ArangoDB: Citation networks, shared speakers, topic similarity
```

### 4. Store Transcript (Automatic enrichment)
```python
video_data = {
    'video_id': 'abc123',
    'title': 'Deep Learning Tutorial',
    'transcript': '...',
    'channel_name': 'AI Academy'
}

# Automatically extracts citations, speakers, entities
doc_id = await search.store_transcript(video_data)
```

## Migration Between Backends

### SQLite → ArangoDB
```python
from youtube_transcripts.arango_integration import YouTubeTranscriptGraph

# Migrate existing SQLite data
graph = YouTubeTranscriptGraph()
graph.migrate_from_sqlite("youtube_transcripts.db")
```

### Running Both (Development/Testing)
```python
# Use SQLite for local testing
test_search = UnifiedSearchV2({'backend': 'sqlite'})

# Use ArangoDB for production
prod_search = UnifiedSearchV2({'backend': 'arangodb'})
```

## Backend Selection Logic

When `YOUTUBE_DB_BACKEND=auto`, the system:

1. Checks if ArangoDB Python client is installed
2. Attempts to connect to ArangoDB server
3. Falls back to SQLite if ArangoDB unavailable
4. Logs which backend is being used

## Performance Considerations

### SQLite Performance
- **Pros**: Fast startup, no network latency, simple queries
- **Cons**: Limited to single machine, no distributed queries
- **Best for**: < 1M transcripts, single-user, development

### ArangoDB Performance
- **Pros**: Scales horizontally, complex queries, graph traversal
- **Cons**: Network latency, requires server setup
- **Best for**: Large datasets, multi-user, production

## Granger Ecosystem Integration

When using ArangoDB backend, YouTube Transcripts integrates with:

1. **Shared Collections**
   - Can query across all Granger modules
   - Unified entity resolution
   - Cross-module relationships

2. **Example Cross-Module Query**
   ```aql
   // Find videos discussing papers processed by Marker
   FOR paper IN marker_papers
       FOR citation IN youtube_citations
           FILTER citation.identifier == paper.arxiv_id
           FOR video IN 1..1 INBOUND citation youtube_cites
               RETURN {paper: paper, video: video}
   ```

3. **Orchestrator Benefits**
   - Module communicator can query both systems
   - Unified knowledge graph
   - Consistent data model

## Recommendations

1. **For Development**: Use SQLite (no setup required)
2. **For Research**: Use ArangoDB (advanced features)
3. **For Production**: Use ArangoDB (scalability)
4. **For Distribution**: Support both (user choice)

## Future Enhancements

1. **Hybrid Mode**: Use SQLite for search, ArangoDB for relationships
2. **Sync Mode**: Keep SQLite and ArangoDB in sync
3. **Migration Tools**: Better SQLite ↔ ArangoDB migration
4. **Performance Profiling**: Auto-select based on query type

## Conclusion

The dual database support makes YouTube Transcripts flexible enough for:
- **Standalone users** who want a simple tool
- **Researchers** who need advanced features
- **Granger integration** with shared knowledge base

This architecture can be applied to ArXiv MCP Server as well, providing the same flexibility.