# YouTube Transcripts - ArangoDB Migration Guide

## Overview

This guide outlines the migration from SQLite to ArangoDB for YouTube Transcripts, aligning with the Granger ecosystem and enabling advanced research features like bolster/contradict analysis.

## Why Migrate to ArangoDB?

### Current Limitations (SQLite)
- Only BM25 text search
- No graph relationships
- No semantic search
- Limited to simple queries
- No integration with other Granger modules

### Benefits of ArangoDB
- **Graph Relationships**: Citation networks, speaker connections, entity linking
- **Semantic Search**: Vector embeddings for conceptual search
- **Hybrid Search**: Combine BM25, semantic, and graph traversal
- **Research Features**: Bolster/contradict analysis, comparative analysis
- **Granger Integration**: Unified memory bank across all modules
- **Temporal Analysis**: Track how knowledge evolves
- **Scalability**: Handle millions of transcripts

## New Features Enabled

### 1. Bolster/Contradict Analysis
```python
from youtube_transcripts.research_analyzer import ResearchAnalyzer

analyzer = ResearchAnalyzer(arango_client)

# Find evidence supporting a claim
evidence = await analyzer.find_evidence(
    "Transformers outperform RNNs for long sequences",
    evidence_type="both"
)

for e in evidence:
    print(f"{e.evidence_type}: {e.text} (confidence: {e.confidence})")
```

### 2. Citation Networks
```python
from youtube_transcripts.arango_integration import YouTubeTranscriptGraph

graph = YouTubeTranscriptGraph()

# Build citation network
network = await graph.get_citation_network("video_id", depth=3)

# Find videos citing the same papers
related = await graph.find_related_videos("video_id")
```

### 3. Speaker Networks
```python
# Find all videos by a speaker
aql = """
FOR speaker IN youtube_speakers
    FILTER speaker.name == @speaker_name
    FOR video IN 1..1 INBOUND speaker youtube_speaks_in
        RETURN video
"""
```

### 4. Comparative Analysis
```python
# Compare explanations across videos
comparisons = await analyzer.compare_explanations("attention mechanism")

for comp in comparisons:
    print(f"Video 1: {comp.video1['title']}")
    print(f"Video 2: {comp.video2['title']}")
    print(f"Consensus: {comp.consensus}")
    print(f"Differences: {comp.differences}")
```

## Migration Steps

### 1. Install Dependencies
```bash
# Add to pyproject.toml
uv add python-arango
uv add arangodb  # Granger's ArangoDB utilities
```

### 2. Set Up ArangoDB
```bash
# Using Docker
docker run -d \
  -p 8529:8529 \
  -e ARANGO_ROOT_PASSWORD=password \
  --name youtube_arango \
  arangodb/arangodb:latest
```

### 3. Run Migration Script
```python
from youtube_transcripts.arango_integration import YouTubeTranscriptGraph

# Initialize ArangoDB
graph = YouTubeTranscriptGraph(
    db_name="memory_bank",
    username="root",
    password="password"
)

# Migrate from SQLite
graph.migrate_from_sqlite("youtube_transcripts.db")
```

### 4. Update Configuration
```python
# config.py
ARANGO_CONFIG = {
    "host": "http://localhost:8529",
    "database": "memory_bank",
    "username": "root",
    "password": "password"
}

# Use ArangoDB instead of SQLite
USE_ARANGODB = True
```

## Data Model

### Collections

1. **youtube_transcripts** (Documents)
   - video_id, title, transcript, embedding
   - channel_name, upload_date, metadata

2. **youtube_speakers** (Documents)
   - name, affiliation, credentials
   - topics, expertise areas

3. **youtube_citations** (Documents)
   - type (arxiv, doi, isbn, etc.)
   - identifier, text, metadata

4. **youtube_entities** (Documents)
   - text, type, category
   - Linked to knowledge graph

5. **youtube_claims** (Documents)
   - claim text, source, confidence
   - For bolster/contradict tracking

### Edge Collections

1. **youtube_cites**: transcript → citation
2. **youtube_speaks_in**: speaker → transcript
3. **youtube_mentions**: transcript → entity
4. **youtube_supports**: transcript → claim
5. **youtube_contradicts**: transcript → claim
6. **youtube_related_to**: transcript → transcript

## Query Examples

### Find Videos Supporting a Claim
```aql
FOR claim IN youtube_claims
    FILTER claim.text == @claim_text
    FOR video IN 1..1 INBOUND claim youtube_supports
        RETURN {
            video: video,
            confidence: FIRST(
                FOR e IN youtube_supports
                    FILTER e._from == video._id AND e._to == claim._id
                    RETURN e.confidence
            )
        }
```

### Citation Network Analysis
```aql
FOR video IN youtube_transcripts
    LET citations = (
        FOR c IN 1..1 OUTBOUND video youtube_cites
            RETURN c
    )
    LET citing_videos = (
        FOR c IN citations
            FOR v IN 1..1 INBOUND c youtube_cites
                FILTER v._id != video._id
                RETURN DISTINCT v
    )
    RETURN {
        video: video,
        citations: LENGTH(citations),
        related_videos: LENGTH(citing_videos)
    }
```

### Speaker Expertise Network
```aql
FOR speaker IN youtube_speakers
    LET videos = (
        FOR v IN 1..1 INBOUND speaker youtube_speaks_in
            RETURN v
    )
    LET topics = UNIQUE(FLATTEN(
        FOR v IN videos
            FOR e IN 1..1 OUTBOUND v youtube_mentions
                FILTER e.type == "TECHNICAL_TERM"
                RETURN e.text
    ))
    RETURN {
        speaker: speaker,
        video_count: LENGTH(videos),
        expertise: topics
    }
```

## Integration with Granger Modules

### 1. Unified Memory Bank
All YouTube transcript data becomes part of Granger's knowledge graph:
- SPARTA can analyze security-related videos
- Marker can link to papers mentioned in videos
- Claude Max Proxy can query across all content

### 2. Cross-Module Queries
```python
# Find videos discussing papers processed by Marker
aql = """
FOR paper IN marker_papers
    FOR citation IN youtube_citations
        FILTER citation.identifier == paper.arxiv_id
        FOR video IN 1..1 INBOUND citation youtube_cites
            RETURN {
                paper: paper,
                video: video,
                citation: citation
            }
"""
```

### 3. Orchestrator Integration
The Module Communicator can now:
- Validate video claims against ArXiv papers
- Find supporting evidence across modules
- Build comprehensive knowledge networks

## Performance Considerations

1. **Indexing Strategy**
   - Full-text indexes on transcript, title
   - Hash indexes on video_id, speaker names
   - Persistent indexes on embeddings

2. **Embedding Generation**
   - Use Granger's embedding utilities
   - Cache embeddings to avoid recomputation
   - Batch processing for efficiency

3. **Query Optimization**
   - Use graph traversal for relationships
   - Leverage AQL optimizer hints
   - Implement pagination for large results

## Backwards Compatibility

During migration, maintain compatibility:

```python
class HybridDatabase:
    def __init__(self):
        self.sqlite = SQLiteDB()
        self.arango = YouTubeTranscriptGraph()
    
    def search(self, query, use_arango=True):
        if use_arango and self.arango.available():
            return self.arango.hybrid_search(query)
        else:
            return self.sqlite.search(query)
```

## Timeline

1. **Phase 1** (Week 1): Set up ArangoDB, create collections
2. **Phase 2** (Week 2): Migrate existing data
3. **Phase 3** (Week 3): Implement research features
4. **Phase 4** (Week 4): Integration testing with Granger
5. **Phase 5** (Week 5): Performance optimization

## Conclusion

Migrating to ArangoDB transforms YouTube Transcripts from a simple search tool into a comprehensive research platform. The graph-based approach enables:

- Citation network analysis
- Evidence-based claim validation
- Speaker expertise mapping
- Cross-video knowledge synthesis
- Deep integration with the Granger ecosystem

This positions YouTube Transcripts as a powerful research tool on par with ArXiv MCP Server, enabling scholarly analysis of educational video content.