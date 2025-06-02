# YouTube Transcripts - Orchestrator Integration Guide

## Overview

This guide describes how the YouTube Transcripts module integrates with the claude-module-communicator orchestrator and coordinates with the arxiv-mcp-server for comprehensive research capabilities.

## Architecture

```
┌─────────────────────────────────────┐
│   Claude Module Communicator        │
│        (Orchestrator)               │
└─────────────┬───────────────────────┘
              │
      ┌───────┴────────┐
      │                │
┌─────▼─────┐   ┌─────▼─────┐
│ YouTube   │   │  ArXiv    │
│Transcripts│◄─►│MCP Server │
└───────────┘   └───────────┘
```

## Module Capabilities

### YouTube Transcripts Module

**Primary Functions:**
- Search YouTube videos (API + local database)
- Fetch and store transcripts
- Extract scientific metadata
- Detect citations and references
- Identify speakers and affiliations
- Classify content by type and level

**Integration Points:**
- Accepts orchestrator messages
- Emits events for important findings
- Forwards validation requests to ArXiv
- Returns structured research data

### Message Protocol

All messages follow this structure:

```json
{
  "source": "module_name",
  "target": "target_module",
  "type": "request|response|event|error",
  "action": "action_name",
  "data": {},
  "correlation_id": "unique_id",
  "timestamp": "ISO8601"
}
```

## Supported Actions

### 1. Search Videos
Find videos based on query, with optional YouTube API search.

**Request:**
```json
{
  "action": "search",
  "data": {
    "query": "transformer architecture",
    "use_youtube_api": false,
    "use_widening": true,
    "extract_citations": true,
    "filters": {
      "limit": 10,
      "channel": "3Blue1Brown",
      "published_after": "2024-01-01"
    }
  }
}
```

**Response:**
```json
{
  "data": {
    "results": [...],
    "widening_info": {
      "original_query": "...",
      "expanded_query": "...",
      "explanation": "..."
    },
    "total_results": 10
  }
}
```

### 2. Fetch Transcript
Get transcript for a specific video.

**Request:**
```json
{
  "action": "fetch_transcript",
  "data": {
    "video_id": "dQw4w9WgXcQ",
    "extract_metadata": true,
    "extract_citations": true
  }
}
```

**Response:**
```json
{
  "data": {
    "transcript": "Full transcript text...",
    "metadata": {
      "entities": [...],
      "speakers": [...],
      "institutions": [...]
    },
    "citations": [
      {
        "type": "arxiv",
        "identifier": "1706.03762",
        "context": "..."
      }
    ]
  }
}
```

### 3. Extract Citations
Extract all citations from text or video.

**Request:**
```json
{
  "action": "extract_citations",
  "data": {
    "text": "As shown in arXiv:1706.03762...",
    "group_by_type": true
  }
}
```

**Response:**
```json
{
  "data": {
    "citations": [...],
    "grouped": {
      "arxiv": [...],
      "doi": [...],
      "author_year": [...]
    }
  }
}
```

### 4. Extract Metadata
Extract scientific metadata from content.

**Request:**
```json
{
  "action": "extract_metadata",
  "data": {
    "video_id": "abc123",
    "include_scientific": true
  }
}
```

**Response:**
```json
{
  "data": {
    "entities": [...],
    "speakers": [...],
    "metrics": [...],
    "scientific": {
      "content_type": "lecture",
      "academic_level": "graduate",
      "has_citations": true,
      "technical_depth": 0.8
    }
  }
}
```

### 5. Validate Content
Prepare content for validation against academic sources.

**Request:**
```json
{
  "action": "validate_content",
  "data": {
    "video_id": "xyz789"
  }
}
```

**Response:**
```json
{
  "data": {
    "validation_requests": [
      {
        "claim": "Transformers achieve 28.4 BLEU",
        "reference": "1706.03762",
        "source": "youtube:xyz789"
      }
    ],
    "forward_to": "arxiv_mcp_server",
    "action": "validate_claims"
  }
}
```

### 6. Find Related Content
Find related videos or suggest paper searches.

**Request:**
```json
{
  "action": "find_related",
  "data": {
    "paper_id": "arXiv:1706.03762"
  }
}
```

**Response:**
```json
{
  "data": {
    "videos": [...],
    "suggested_searches": [
      "transformer architecture",
      "self-attention mechanism"
    ]
  }
}
```

## Event Types

The module can emit these events:

### Citation Found
```json
{
  "event": "citation_found",
  "data": {
    "video_id": "abc123",
    "citation": {
      "type": "arxiv",
      "identifier": "1706.03762"
    }
  }
}
```

### High-Value Content
```json
{
  "event": "high_value_content",
  "data": {
    "video_id": "xyz789",
    "indicators": {
      "citation_count": 15,
      "speaker_credentials": "PhD",
      "content_type": "lecture"
    }
  }
}
```

## Integration Patterns

### 1. Sequential Research Flow
```python
# Orchestrator coordinates sequential steps
async def research_topic(topic: str):
    # Step 1: Search YouTube
    youtube_results = await youtube.search(topic)
    
    # Step 2: Extract papers mentioned
    papers = []
    for video in youtube_results:
        citations = await youtube.extract_citations(video.id)
        papers.extend(citations)
    
    # Step 3: Validate with ArXiv
    for paper in papers:
        validation = await arxiv.validate(paper)
    
    return combined_results
```

### 2. Parallel Discovery
```python
# Orchestrator runs parallel searches
async def discover_research(query: str):
    # Search both sources simultaneously
    youtube_task = youtube.search(query)
    arxiv_task = arxiv.search_papers(query)
    
    youtube_results, arxiv_results = await asyncio.gather(
        youtube_task, arxiv_task
    )
    
    # Cross-reference
    return cross_reference(youtube_results, arxiv_results)
```

### 3. Event-Driven Validation
```python
# Orchestrator responds to events
@orchestrator.on("youtube.citation_found")
async def handle_citation(event):
    # Automatically validate citation
    paper = await arxiv.get_paper(event.citation.identifier)
    
    if paper:
        validation = await arxiv.validate_claim(
            event.citation.context,
            paper.id
        )
        
        # Notify user of validation result
        await notify_validation(validation)
```

## Configuration

### YouTube Module Setup
```python
from youtube_transcripts.orchestrator_integration import YouTubeResearchModule

# Initialize module
youtube_module = YouTubeResearchModule(config)

# Register with orchestrator
orchestrator.register_module("youtube_transcripts", youtube_module)

# Set up event handlers
youtube_module.register_handler("citation_validation_complete", 
                               handle_validation_result)
```

### Environment Variables
```bash
# YouTube API
YOUTUBE_API_KEY=your-key-here

# Database
DATABASE_PATH=./youtube_transcripts.db

# Search settings
MAX_SEARCH_RESULTS=50
ENABLE_SEARCH_WIDENING=true

# Integration
ORCHESTRATOR_URL=http://localhost:8000
MODULE_NAME=youtube_transcripts
```

## Error Handling

### Common Errors

1. **Transcript Not Available**
```json
{
  "type": "error",
  "error": "No transcript available for video xyz789",
  "recovery": "Try alternative video or enable auto-captions"
}
```

2. **API Quota Exceeded**
```json
{
  "type": "error", 
  "error": "YouTube API quota exceeded",
  "recovery": "Use local search or wait until quota resets"
}
```

3. **Invalid Citation Format**
```json
{
  "type": "error",
  "error": "Cannot parse citation: 'Smith et al 2023'",
  "recovery": "Provide more specific citation format"
}
```

### Error Recovery Strategies

```python
async def robust_search(query: str):
    try:
        # Try YouTube API first
        return await youtube.search_youtube_api(query)
    except QuotaExceededError:
        # Fall back to local search
        logger.warning("API quota exceeded, using local search")
        return await youtube.search_local(query)
    except Exception as e:
        # Log and return partial results
        logger.error(f"Search error: {e}")
        return {"results": [], "error": str(e)}
```

## Performance Optimization

### Caching Strategy
- Cache transcripts indefinitely (immutable)
- Cache search results for 1 hour
- Cache metadata extraction for 24 hours
- Share citation cache with ArXiv module

### Batch Operations
```python
# Batch citation extraction
citations = await youtube.extract_citations_batch([
    video1_id, video2_id, video3_id
])

# Batch metadata extraction
metadata = await youtube.extract_metadata_batch(video_ids)
```

### Async Processing
- Use asyncio for all I/O operations
- Process multiple videos concurrently
- Stream large transcripts instead of loading fully

## Monitoring & Metrics

### Key Metrics
- Search response time
- Citation extraction accuracy
- API quota usage
- Cache hit rate
- Error rate by type

### Health Check Endpoint
```python
async def health_check():
    return {
        "status": "healthy",
        "youtube_api": check_youtube_api(),
        "database": check_database(),
        "cache": check_cache(),
        "last_error": get_last_error()
    }
```

## Security Considerations

1. **API Key Protection**
   - Store in environment variables
   - Never log or expose keys
   - Rotate regularly

2. **Input Validation**
   - Sanitize search queries
   - Validate video IDs
   - Limit batch sizes

3. **Rate Limiting**
   - Respect YouTube API limits
   - Implement backoff strategies
   - Queue requests if needed

## Future Enhancements

1. **Real-time Monitoring**
   - WebSocket support for live events
   - Subscribe to channel updates
   - Alert on new relevant content

2. **Advanced Analytics**
   - Citation trend analysis
   - Speaker influence metrics
   - Content quality scoring

3. **Multi-language Support**
   - Transcript translation
   - Cross-language search
   - International paper matching

This integration enables powerful research workflows combining the accessibility of YouTube content with the rigor of academic literature through the ArXiv MCP server.