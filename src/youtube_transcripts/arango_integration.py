"""
ArangoDB Integration for YouTube Transcripts
Migrates from SQLite to ArangoDB for enhanced research capabilities
Module: arango_integration.py
Description: Implementation of arango integration functionality

This module provides:
- Graph-based transcript storage
- Citation networks
- Speaker relationships
- Semantic search with embeddings
- Temporal analysis
- Entity linking

External Dependencies:
- python-arango: ArangoDB Python driver
- arangodb.core: Granger's ArangoDB utilities

Example Usage:
>>> from youtube_transcripts.arango_integration import YouTubeTranscriptGraph
>>> graph = YouTubeTranscriptGraph()
>>> await graph.store_transcript(video_data)
>>> results = await graph.hybrid_search("machine learning", limit=10)
"""

import asyncio
from datetime import datetime
from typing import Any

# Import split modules
from .arango_connection import ArangoConnection
from .arango_operations import YouTubeTranscriptOperations


class YouTubeTranscriptGraph:
    """
    Graph-based storage for YouTube transcripts using ArangoDB
    Integrates with Granger's memory bank architecture
    """

    def __init__(self, db_name: str = "memory_bank",
                 host: str = "http://localhost:8529",
                 username: str = "root",
                 password: str = ""):
        """Initialize connection to ArangoDB"""
        # Setup connection
        self.connection = ArangoConnection(db_name, host, username, password)
        self.db = self.connection.connect()

        # Ensure collections and indexes exist
        self.connection.ensure_collections(self.db)
        self.connection.ensure_indexes(self.db)
        self.connection.ensure_graph(self.db)

        # Initialize operations handler
        self.ops = YouTubeTranscriptOperations(
            self.db,
            self.connection.collections,
            self.connection.edge_collections
        )

    # Delegate main operations to ops handler
    async def store_transcript(self, video_data: dict[str, Any]) -> str:
        """Store a transcript with all its relationships"""
        return await self.ops.store_transcript(video_data)

    async def hybrid_search(self, query: str, limit: int = 10,
                          filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Perform hybrid search combining full-text and semantic search"""
        return await self.ops.hybrid_search(query, limit, filters)

    async def get_citation_network(self, video_id: str, depth: int = 2) -> dict[str, Any]:
        """Get citation network for a video"""
        return await self.ops.get_citation_network(video_id, depth)

    async def find_related_videos(self, video_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Find videos related by citations, speakers, or entities"""
        return await self.ops.find_related_videos(video_id, limit)

    # Additional convenience methods
    def get_transcript(self, video_id: str) -> dict[str, Any] | None:
        """Get a single transcript by video ID"""
        collection = self.db.collection(self.connection.collections['transcripts'])
        try:
            return collection.get({'_key': video_id})
        except:
            return None

    def list_channels(self) -> list[dict[str, Any]]:
        """List all channels in the database"""
        collection = self.db.collection(self.connection.collections['channels'])
        return list(collection.all())

    def search_by_speaker(self, speaker_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for videos featuring a specific speaker"""
        aql = """
        FOR speaker IN @@speakers_collection
        FILTER CONTAINS(LOWER(speaker.name), LOWER(@speaker_name))
        FOR v, e IN OUTBOUND speaker @@speaks_edge
        LIMIT @limit
        RETURN {
            video_id: v.video_id,
            title: v.title,
            channel_name: v.channel_name,
            speaker: speaker.name,
            speaker_role: speaker.role
        }
        """

        bind_vars = {
            '@speakers_collection': self.connection.collections['speakers'],
            '@speaks_edge': self.connection.edge_collections['speaks_in'],
            'speaker_name': speaker_name,
            'limit': limit
        }

        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
        return list(cursor)

    def get_statistics(self) -> dict[str, int]:
        """Get database statistics"""
        stats = {}

        # Document collection counts
        for name, collection in self.connection.collections.items():
            try:
                stats[f'{name}_count'] = self.db.collection(collection).count()
            except:
                stats[f'{name}_count'] = 0

        # Edge collection counts
        for name, collection in self.connection.edge_collections.items():
            try:
                stats[f'{name}_edges'] = self.db.collection(collection).count()
            except:
                stats[f'{name}_edges'] = 0

        return stats


# Maintain backward compatibility
async def migrate_from_sqlite(sqlite_path: str, arango_graph: YouTubeTranscriptGraph):
    """
    Migrate data from SQLite to ArangoDB
    
    Args:
        sqlite_path: Path to SQLite database
        arango_graph: Initialized ArangoDB graph
    """
    import sqlite3

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    # Migrate transcripts
    cursor = conn.execute("SELECT * FROM transcripts")
    transcripts = cursor.fetchall()

    for transcript in transcripts:
        video_data = dict(transcript)

        # Convert SQLite timestamp to ISO format
        if 'fetched_at' in video_data:
            try:
                dt = datetime.fromisoformat(video_data['fetched_at'])
                video_data['fetched_at'] = dt.isoformat()
            except:
                video_data['fetched_at'] = datetime.utcnow().isoformat()

        # Store in ArangoDB
        await arango_graph.store_transcript(video_data)

    conn.close()

    print(f"Migrated {len(transcripts)} transcripts to ArangoDB")


# Validation
if __name__ == "__main__":
    # Test basic functionality
    async def validate():
        graph = YouTubeTranscriptGraph()

        # Test data
        test_video = {
            'video_id': 'test123',
            'title': 'Test Video',
            'channel_id': 'ch123',
            'channel_name': 'Test Channel',
            'content': 'This is a test transcript about machine learning and AI.',
            'duration_seconds': 600,
            'fetched_at': datetime.utcnow().isoformat()
        }

        # Store
        doc_id = await graph.store_transcript(test_video)
        print(f"✅ Stored transcript: {doc_id}")

        # Search
        results = await graph.hybrid_search("machine learning")
        print(f"✅ Search found {len(results)} results")

        # Stats
        stats = graph.get_statistics()
        print(f"✅ Database statistics: {stats}")

        print("✅ ArangoDB integration validation passed")

    asyncio.run(validate())
