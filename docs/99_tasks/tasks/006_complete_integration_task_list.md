
# Complete Task List: YouTube Transcripts + ArangoDB Integration

This task list follows the `TASK_LIST_TEMPLATE_GUIDE_V2.md` format for integrating existing ArangoDB and Claude Module Communicator functionality.

---

## Task 001: Enhance GraphMemoryIntegration with Entity Extraction

**Test ID**: `graph_memory_001_entity_extraction`  
**Model**: N/A (uses existing functionality)  
**Goal**: Add entity extraction to GraphMemoryIntegration class

### Working Code Example

Add this method to the `GraphMemoryIntegration` class in `src/youtube_transcripts/unified_search.py`:

```python
from arangodb.core.graph.entity_resolution import EntityResolver

def store_transcript_with_entities(self, video_data: Dict[str, Any]) -> Optional[str]:
    if not self.enabled:
        return None

    try:
        # Create memory for the transcript
        memory_id = self.conversation_manager.create_memory(
            user_input=f"YouTube Video: {video_data['title']}",
            agent_response=video_data['transcript'],
            metadata={
                'source': 'youtube',
                'video_id': video_data['video_id'],
                'channel': video_data['channel_name'],
                'publish_date': video_data['publish_date']
            }
        )

        # Use existing entity extraction
        resolver = EntityResolver(self.memory_bank.db)
        entities = resolver.extract_entities_from_text(video_data['transcript'])

        # Store entities using existing knowledge manager
        for entity in entities:
            self.knowledge_manager.add_entity(entity)

        logger.info(f"Stored transcript with {len(entities)} entities")
        return memory_id

    except Exception as e:
        logger.error(f"Failed to store transcript: {e}")
        return None
```

### Test Details

**Run Command**:
```bash
python -c "from youtube_transcripts.unified_search import UnifiedYouTubeSearch; s = UnifiedYouTubeSearch(); print(s.graph_memory.enabled)"
```

**Expected Output Structure**:
```
Stored transcript with 2 entities
Result: mem_abc123def456
```

### Common Issues & Solutions

#### Issue 1: ArangoDB not initialized  
**Solution**: Check if enabled before calling

#### Issue 2: Entity extraction timeout  
**Solution**: Chunk large transcripts into smaller pieces

### Validation Requirements

- Memory ID is created successfully
- Entity count is greater than 0
- No exceptions thrown

---

## Task 002: Add Relationship Extraction Between Transcripts

**Test ID**: `graph_memory_002_relationships`  
**Model**: N/A (uses existing functionality)  
**Goal**: Extract relationships between stored transcripts

### Working Code Example

Add to `GraphMemoryIntegration` class:

```python
from arangodb.core.graph.relationship_extraction import extract_relationships_from_text

def extract_transcript_relationships(self, video_id: str, limit: int = 10) -> List[Dict]:
    if not self.enabled:
        return []

    try:
        # Get the memory for this video
        memory_query = """
        FOR m IN memories
        FILTER m.metadata.video_id == @video_id
        RETURN m
        """
        cursor = self.memory_bank.db.aql.execute(
            memory_query,
            bind_vars={'video_id': video_id}
        )
        memory = cursor.next()

        if not memory:
            return []

        # Extract relationships using existing functionality
        relationships = extract_relationships_from_text(
            self.memory_bank.db,
            memory['agent_response'],
            source_doc_id=memory['_id']
        )

        return {
            'extracted_relationships': relationships,
            'similar_videos': []  # Can be enhanced
        }

    except Exception as e:
        logger.error(f"Failed to extract relationships: {e}")
        return {}
```

### Test Details

**Run Command**:
```bash
python -c "from youtube_transcripts.unified_search import UnifiedYouTubeSearch; s = UnifiedYouTubeSearch(); print('Ready')"
```

**Expected Output Structure**:
```json
{
  "extracted_relationships": [
    {
      "from": "ByteDance",
      "to": "VERL",
      "type": "CREATED",
      "confidence": 0.9
    }
  ]
}
```

### Validation Requirements

- Returns dictionary with expected keys
- No exceptions for missing videos
- Handles disabled ArangoDB gracefully

---

## Task 003: Enhance Search with ArangoDB Hybrid Search

**Test ID**: `search_003_hybrid_fallback`  
**Model**: N/A (search enhancement)  
**Goal**: Use ArangoDB hybrid search when SQLite returns few results

### Working Code Example

Add new method to `UnifiedYouTubeSearch`:

```python
from arangodb.core.search.hybrid_search import HybridSearch

def search_with_fallback(self, query: str, channels: Optional[List[str]] = None, 
                        limit: int = 10) -> Dict[str, Any]:
    # First try SQLite FTS
    sqlite_results = search_transcripts(query, channels, limit, self.db_path)

    # If we have good results, return them
    if len(sqlite_results) >= 5:
        return {
            'results': sqlite_results,
            'source': 'sqlite_fts',
            'fallback_used': False
        }

    # Otherwise, try ArangoDB if available
    if self.graph_memory.enabled:
        try:
            # Use existing hybrid search
            hybrid_search = HybridSearch(self.graph_memory.memory_bank.db)

            # Search with YouTube filter
            arango_results = hybrid_search.search(
                query=query,
                collections=['memories'],
                filters={'metadata.source': 'youtube'},
                limit=limit * 2
            )

            # Convert and combine results
            # ... conversion logic ...

            return {
                'results': combined_results[:limit],
                'source': 'combined',
                'fallback_used': True
            }

        except Exception as e:
            logger.error(f"ArangoDB search failed: {e}")

    return {
        'results': sqlite_results,
        'source': 'sqlite_fts',
        'fallback_used': False
    }
```

### Test Details

**Run Command**:
```bash
python -c "from youtube_transcripts.unified_search import UnifiedYouTubeSearch; s = UnifiedYouTubeSearch(); r = s.search('test'); print(len(r['results']))"
```

**Expected Output Structure**:
```json
{
  "results": [...],
  "source": "combined",
  "fallback_used": true,
  "sqlite_count": 2,
  "arango_count": 8
}
```

### Validation Requirements

- Always returns results (even if empty)
- Source field indicates which backend was used
- Fallback flag correctly set

---

## Task 004: Add Transcript Chunking with Progress Tracking

**Test ID**: `processing_004_chunk_tracking`  
**Model**: `claude-3-opus-20240229`  
**Goal**: Chunk transcripts and track progress using ModuleCommunicator

### Working Code Example

Create new file `src/youtube_transcripts/processing/transcript_chunker.py`:

```python
from claude_module_communicator import ModuleCommunicator
import anthropic
import json

class TranscriptChunker:
    def __init__(self):
        self.communicator = ModuleCommunicator('youtube_transcript_chunker')
        self.claude = anthropic.Anthropic()

    async def chunk_transcript(self, video_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        task_id = f"chunk_{video_data['video_id']}"

        # Start progress tracking
        self.communicator.track_progress(task_id, 0, 100)

        # Call Claude for chunking
        # ... chunking logic ...

        self.communicator.track_progress(task_id, 100, 100)

        return chunks
```

### Test Details

**Run Command**:
```bash
cd src/youtube_transcripts/processing && python transcript_chunker.py
```

**Expected Output Structure**:
```
Created 3 chunks
Progress: {'percentage': 100, 'status': 'completed'}
```

### Validation Requirements

- Creates at least one chunk
- Progress reaches 100%
- All chunks have required fields

---

## Task 005: Create Graph-Based Learning Paths

**Test ID**: `graph_005_learning_paths`  
**Model**: N/A (graph traversal)  
**Goal**: Generate learning paths using ArangoDB graph traversal

### Working Code Example

Create `src/youtube_transcripts/graph/learning_paths.py`:

```python
from arangodb.core.search.graph_traverse import GraphTraversal

class YouTubeLearningPaths:
    def __init__(self, arango_db):
        self.db = arango_db
        self.graph_traversal = GraphTraversal(self.db)

    def find_learning_path(self, start_topic: str, end_topic: str) -> List[Dict]:
        # Find videos containing topics
        # Use graph traversal to find path
        # Return ordered learning sequence
        pass
```

### Test Details

**Run Command**:
```bash
python src/youtube_transcripts/graph/learning_paths.py
```

**Expected Output Structure**:
```
Learning path with 4 steps:
1. Python Programming Fundamentals
2. Data Structures in Python
3. NumPy and Pandas Tutorial
4. Introduction to Machine Learning
```

### Validation Requirements

- Returns list of videos
- Path makes logical sense
- Handles no path found gracefully

---

## Task 006: Add CLI Commands for Enhanced Features

**Test ID**: `cli_006_enhanced_commands`  
**Model**: N/A (CLI integration)  
**Goal**: Add commands that expose ArangoDB-enhanced features

### Working Code Example

Add to `src/youtube_transcripts/cli/app.py`:

```python
@app.command()
def store_with_graph(video_id: str, extract_entities: bool = True):
    search = UnifiedYouTubeSearch()

    if not search.graph_memory.enabled:
        console.print("[red]ArangoDB not available[/red]")
        return

    # Get transcript and store with entities
    # ... implementation ...

@app.command()
def search_hybrid(query: str, limit: int = 10):
    search = UnifiedYouTubeSearch()
    results = search.search_with_fallback(query, limit=limit)
    # Display results
```

### Test Details

**Run Commands**:
```bash
youtube-transcripts store-with-graph abc123
youtube-transcripts search-hybrid "VERL distributed training"
```

**Expected Output Structure**:
```
✓ Stored as memory: mem_xyz789
✓ Found 5 relationships

Hybrid Search Results
━━━━━━━━━━━━━━━━━━━━━
Title: VERL Tutorial
Source: arango
```

### Validation Requirements

- Commands are registered in CLI
- Error handling for missing ArangoDB
- Clear user feedback

---

## Task 007: Integration Testing

**Test ID**: `integration_007_full_flow`  
**Model**: N/A (testing)  
**Goal**: Test complete integration flow

### Working Code Example

Create `tests/test_arango_integration.py`:

```python
import pytest
from youtube_transcripts.unified_search import UnifiedYouTubeSearch

class TestArangoIntegration:
    @pytest.mark.asyncio
    async def test_complete_flow(self):
        search = UnifiedYouTubeSearch()

        if not search.graph_memory.enabled:
            pytest.skip("ArangoDB not available")

        # Test complete flow
        # 1. Store transcript
        # 2. Extract entities
        # 3. Search with hybrid
        # 4. Verify results
```

### Test Details

**Run Command**:
```bash
pytest tests/test_arango_integration.py -v
```

**Expected Output Structure**:
```
test_arango_integration.py::TestArangoIntegration::test_complete_flow PASSED
========================= 1 passed in 3.45s =========================
```

### Validation Requirements

- All integration points tested
- Graceful handling of missing dependencies
- Clear test output

---

## Summary

This task list provides 7 concrete implementation tasks that:

1. Leverage existing ArangoDB functionality (no duplication)
2. Use existing Claude Module Communicator for progress tracking
3. Enhance search capabilities without replacing existing code
4. Add CLI commands for new features
5. Include comprehensive testing

**Key principles:**
- Import and use existing modules
- Focus on integration glue code
- Let YouTube transcripts handle YouTube-specific logic
- Let ArangoDB handle graph operations
- Let Claude Module Communicator handle progress tracking

No code duplication, maximum functionality reuse.

