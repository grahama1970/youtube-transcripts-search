# ArangoDB Setup for YouTube Transcripts

This guide explains how to set up and use ArangoDB as the storage backend for the YouTube transcripts project.

## Prerequisites

- Docker installed and running
- Python 3.9+ with `uv` package manager
- ArangoDB credentials (default: root/openSesame)

## Quick Start

### 1. Using Existing ArangoDB Instance

If you already have ArangoDB running (like from the `/home/graham/workspace/experiments/arangodb/` project):

```bash
# The instance is already running on port 8529
# Credentials: root / openSesame
```

### 2. Starting Fresh with Docker

If you need a new instance:

```bash
# Start ArangoDB using docker-compose
docker-compose up -d arangodb

# Or manually with docker
docker run -d \
  --name youtube_transcripts_arangodb \
  -p 8529:8529 \
  -e ARANGO_ROOT_PASSWORD=openSesame \
  arangodb/arangodb:latest
```

### 3. Initialize Database

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies if needed
uv add python-arango python-dotenv loguru

# Run setup script
python scripts/setup_arangodb.py
```

## Database Structure

The setup creates the following collections:

### Document Collections

1. **transcripts** - Main transcript storage
   - video_id (unique)
   - channel info
   - metadata
   - full transcript text
   - segments with timestamps

2. **transcript_chunks** - For semantic search
   - Chunked transcript text
   - Embeddings for vector search
   - Time boundaries
   - Links to parent transcript

3. **entities** - Extracted entities
   - People, organizations, topics
   - Metadata and descriptions

4. **search_history** - Analytics
   - Query tracking
   - User behavior
   - Performance metrics

### Edge Collections

1. **entity_mentions** - Entity relationships
   - Links entities to transcripts
   - Context and confidence scores

### Search Views

1. **transcript_search_view** - Full-text search
   - Indexes title, description, transcript text
   - Supports multiple analyzers

## Configuration

Environment variables in `.env`:

```bash
# ArangoDB Configuration
ARANGO_HOST=http://localhost:8529
ARANGO_USER=root
ARANGO_PASSWORD=openSesame
ARANGO_DB_NAME=youtube_transcripts
ARANGO_TEST_DB_NAME=youtube_transcripts_test

# Embedding Configuration (for semantic search)
EMBEDDING_DIMENSION=1024
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
```

## Testing Connection

```python
# Test script
from arango import ArangoClient
import os

client = ArangoClient(hosts=os.getenv("ARANGO_HOST"))
db = client.db(
    os.getenv("ARANGO_DB_NAME"),
    username=os.getenv("ARANGO_USER"),
    password=os.getenv("ARANGO_PASSWORD")
)

# Test query
result = db.aql.execute("FOR t IN transcripts LIMIT 1 RETURN t")
print(list(result))
```

## Common Operations

### Store a Transcript

```python
transcripts = db.collection("transcripts")
transcripts.insert({
    "video_id": "abc123",
    "title": "Introduction to ArangoDB",
    "channel_name": "TechTalks",
    "transcript_text": "Full transcript here...",
    "upload_date": "2024-01-15",
    "tags": ["database", "nosql", "graph"]
})
```

### Search Transcripts

```python
# Full-text search
query = """
FOR doc IN transcript_search_view
  SEARCH ANALYZER(doc.transcript_text IN TOKENS(@query, 'text_en'), 'text_en')
  SORT BM25(doc) DESC
  LIMIT 10
  RETURN doc
"""
results = db.aql.execute(query, bind_vars={"query": "graph databases"})
```

### Vector Search (Semantic)

```python
# Assuming embeddings are stored
query = """
FOR chunk IN transcript_chunks
  LET similarity = DOT_PRODUCT(chunk.embedding, @query_embedding)
  FILTER similarity > 0.7
  SORT similarity DESC
  LIMIT 10
  RETURN MERGE(chunk, {similarity: similarity})
"""
```

## Troubleshooting

### Connection Issues

```bash
# Check if ArangoDB is running
docker ps | grep arangodb

# Check logs
docker logs youtube_transcripts_arangodb

# Test connection
curl -u root:openSesame http://localhost:8529/_api/version
```

### Database Not Found

```bash
# Re-run setup
python scripts/setup_arangodb.py

# Or manually create via ArangoDB Web UI
# Navigate to: http://localhost:8529
# Login: root / openSesame
# Create database: youtube_transcripts
```

### Performance Tuning

1. **Indexes**: The setup script creates basic indexes. Add more as needed:
   ```python
   collection.add_hash_index(fields=["field_name"])
   collection.add_fulltext_index(fields=["text_field"])
   ```

2. **View Optimization**: Adjust analyzers in the search view for better results

3. **Sharding**: For large datasets, consider sharding collections

## Integration with YouTube Transcripts

The ArangoDB setup is designed to work seamlessly with the YouTube transcripts project:

1. **Transcript Storage**: Full transcripts with metadata
2. **Chunking**: Automatic chunking for semantic search
3. **Entity Extraction**: Graph-based entity relationships
4. **Search**: Multiple search strategies (BM25, vector, graph)
5. **Analytics**: Query tracking and optimization

## Next Steps

1. Run the setup script to initialize the database
2. Test the connection with a simple query
3. Start storing YouTube transcripts
4. Implement search functionality
5. Add entity extraction and relationship mapping

For more details, see the main project documentation.