"""
Database Adapter for YouTube Transcripts
Supports both SQLite (standalone) and ArangoDB (Granger integration)
Module: database_adapter.py
Description: Implementation of database adapter functionality

This module provides a unified interface that automatically selects
the appropriate backend based on configuration and availability.

External Dependencies:
- sqlite3: Built-in Python module
- python-arango: Optional, for ArangoDB support

Example Usage:
>>> from youtube_transcripts.database_adapter import DatabaseAdapter
>>> db = DatabaseAdapter()  # Auto-selects based on config
>>> results = await db.search("machine learning")
>>> await db.store_transcript(video_data)
"""

import asyncio
import json
import logging
import sqlite3
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Check for ArangoDB availability
try:
    from arango import ArangoClient

    from .arango_integration import YouTubeTranscriptGraph
    HAS_ARANGO = True
except ImportError:
    HAS_ARANGO = False
    logger.info("ArangoDB not available, will use SQLite backend")


class DatabaseBackend(Protocol):
    """Protocol defining the interface for database backends"""

    async def search(self, query: str, limit: int = 10,
                    filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search for transcripts"""
        ...

    async def store_transcript(self, video_data: dict[str, Any]) -> str:
        """Store a transcript"""
        ...

    async def get_transcript(self, video_id: str) -> dict[str, Any] | None:
        """Retrieve a transcript by ID"""
        ...

    async def find_evidence(self, claim: str, evidence_type: str = "both") -> list[dict[str, Any]]:
        """Find evidence for claims (research feature)"""
        ...

    async def find_related(self, video_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find related videos"""
        ...


class SQLiteBackend:
    """SQLite backend for standalone usage"""

    def __init__(self, db_path: str = "youtube_transcripts.db"):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Initialize SQLite database with FTS5"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main transcripts table with FTS5
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS transcripts
            USING fts5(
                video_id UNINDEXED,
                title,
                channel_name,
                publish_date UNINDEXED,
                transcript,
                summary,
                metadata UNINDEXED,
                tokenize=porter
            )
        ''')

        # Evidence table for research features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim TEXT NOT NULL,
                video_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                text TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                timestamp REAL DEFAULT 0,
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Citations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                citation_type TEXT NOT NULL,
                identifier TEXT,
                text TEXT NOT NULL,
                context TEXT,
                confidence REAL DEFAULT 1.0,
                metadata TEXT
            )
        ''')

        # Speakers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                title TEXT,
                affiliation TEXT,
                credentials TEXT,
                topics TEXT
            )
        ''')

        # Video-Speaker relationship
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_speakers (
                video_id TEXT NOT NULL,
                speaker_id INTEGER NOT NULL,
                role TEXT DEFAULT 'speaker',
                FOREIGN KEY (speaker_id) REFERENCES speakers(id)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence(claim)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_citations_video ON citations(video_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_speakers ON video_speakers(video_id)')

        conn.commit()
        conn.close()

    async def search(self, query: str, limit: int = 10,
                    filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search transcripts using FTS5"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with filters
        base_query = '''
            SELECT video_id, title, channel_name, publish_date, 
                   snippet(transcripts, -1, '<b>', '</b>', '...', 32) as snippet,
                   rank
            FROM transcripts
            WHERE transcripts MATCH ?
        '''

        params = [query]

        if filters:
            if 'channel' in filters:
                base_query += ' AND channel_name = ?'
                params.append(filters['channel'])

            if 'date_after' in filters:
                base_query += ' AND publish_date >= ?'
                params.append(filters['date_after'])

        base_query += ' ORDER BY rank LIMIT ?'
        params.append(limit)

        cursor.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return results

    async def store_transcript(self, video_data: dict[str, Any]) -> str:
        """Store transcript in SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Store main transcript
        metadata = json.dumps(video_data.get('metadata', {}))

        cursor.execute('''
            INSERT OR REPLACE INTO transcripts 
            (video_id, title, channel_name, publish_date, transcript, summary, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_data['video_id'],
            video_data['title'],
            video_data.get('channel_name', ''),
            video_data.get('upload_date', ''),
            video_data['transcript'],
            video_data.get('summary', ''),
            metadata
        ))

        # Store citations if present
        if 'citations' in video_data:
            for citation in video_data['citations']:
                cursor.execute('''
                    INSERT INTO citations 
                    (video_id, citation_type, identifier, text, context, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_data['video_id'],
                    citation['type'],
                    citation.get('id', ''),
                    citation['text'],
                    citation.get('context', ''),
                    citation.get('confidence', 1.0),
                    json.dumps(citation.get('metadata', {}))
                ))

        # Store speakers if present
        if 'speakers' in video_data:
            for speaker in video_data['speakers']:
                # Insert or get speaker
                cursor.execute('''
                    INSERT OR IGNORE INTO speakers (name, title, affiliation)
                    VALUES (?, ?, ?)
                ''', (
                    speaker['name'],
                    speaker.get('title', ''),
                    speaker.get('affiliation', '')
                ))

                cursor.execute('SELECT id FROM speakers WHERE name = ?', (speaker['name'],))
                speaker_id = cursor.fetchone()[0]

                # Link to video
                cursor.execute('''
                    INSERT OR REPLACE INTO video_speakers (video_id, speaker_id, role)
                    VALUES (?, ?, ?)
                ''', (
                    video_data['video_id'],
                    speaker_id,
                    speaker.get('role', 'speaker')
                ))

        conn.commit()
        conn.close()

        return video_data['video_id']

    async def get_transcript(self, video_id: str) -> dict[str, Any] | None:
        """Get transcript by video ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM transcripts WHERE video_id = ?
        ''', (video_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        result = dict(row)

        # Get citations
        cursor.execute('''
            SELECT * FROM citations WHERE video_id = ?
        ''', (video_id,))
        result['citations'] = [dict(row) for row in cursor.fetchall()]

        # Get speakers
        cursor.execute('''
            SELECT s.* FROM speakers s
            JOIN video_speakers vs ON s.id = vs.speaker_id
            WHERE vs.video_id = ?
        ''', (video_id,))
        result['speakers'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return result

    async def find_evidence(self, claim: str, evidence_type: str = "both") -> list[dict[str, Any]]:
        """Find evidence for claims - basic implementation for SQLite"""
        # Search for transcripts mentioning the claim
        results = await self.search(claim, limit=20)

        evidence = []
        for result in results:
            # Basic evidence extraction (without LLM in standalone mode)
            evidence.append({
                'video_id': result['video_id'],
                'title': result['title'],
                'channel': result['channel_name'],
                'text': result['snippet'],
                'confidence': abs(result['rank']),  # Use rank as confidence proxy
                'evidence_type': 'potential',  # Mark as potential without LLM analysis
                'reasoning': 'Text similarity match'
            })

        return evidence

    async def find_related(self, video_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find related videos - basic implementation"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get original video
        cursor.execute('SELECT title, channel_name FROM transcripts WHERE video_id = ?', (video_id,))
        original = cursor.fetchone()

        if not original:
            conn.close()
            return []

        # Find videos by same channel
        cursor.execute('''
            SELECT video_id, title, channel_name, publish_date
            FROM transcripts
            WHERE channel_name = ? AND video_id != ?
            LIMIT ?
        ''', (original['channel_name'], video_id, limit))

        results = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return results


class ArangoBackend:
    """ArangoDB backend for Granger integration"""

    def __init__(self, config: dict[str, Any] | None = None):
        if not HAS_ARANGO:
            raise ImportError("ArangoDB dependencies not installed")

        config = config or {}
        self.graph = YouTubeTranscriptGraph(
            db_name=config.get('database', 'memory_bank'),
            host=config.get('host', 'http://localhost:8529'),
            username=config.get('username', 'root'),
            password=config.get('password', '')
        )

    async def search(self, query: str, limit: int = 10,
                    filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search using ArangoDB hybrid search"""
        return await self.graph.hybrid_search(query, limit, filters)

    async def store_transcript(self, video_data: dict[str, Any]) -> str:
        """Store transcript in ArangoDB"""
        return await self.graph.store_transcript(video_data)

    async def get_transcript(self, video_id: str) -> dict[str, Any] | None:
        """Get transcript from ArangoDB"""
        collection = self.graph.db.collection(self.graph.collections['transcripts'])
        try:
            doc = collection.get(video_id)
            return doc
        except:
            return None

    async def find_evidence(self, claim: str, evidence_type: str = "both") -> list[dict[str, Any]]:
        """Find evidence using ArangoDB and research analyzer"""
        from .research_analyzer import ResearchAnalyzer

        analyzer = ResearchAnalyzer(self.graph.client)
        evidence = await analyzer.find_evidence(claim, evidence_type)

        return [e.to_dict() for e in evidence]

    async def find_related(self, video_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find related videos using graph traversal"""
        return await self.graph.find_related_videos(video_id, limit)


class DatabaseAdapter:
    """
    Unified database adapter that automatically selects backend
    based on configuration and availability
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize database adapter
        
        Args:
            config: Optional configuration dict with:
                - backend: 'sqlite' or 'arangodb' (auto-detect if not specified)
                - sqlite_path: Path to SQLite database
                - arango_config: ArangoDB configuration
        """
        self.config = config or {}
        self.backend = self._initialize_backend()
        logger.info(f"Using {type(self.backend).__name__} backend")

    def _initialize_backend(self) -> DatabaseBackend:
        """Select and initialize appropriate backend"""
        backend_name = self.config.get('backend', 'auto')

        if backend_name == 'sqlite':
            return SQLiteBackend(self.config.get('sqlite_path', 'youtube_transcripts.db'))

        elif backend_name == 'arangodb':
            if not HAS_ARANGO:
                logger.warning("ArangoDB requested but not available, falling back to SQLite")
                return SQLiteBackend(self.config.get('sqlite_path', 'youtube_transcripts.db'))
            return ArangoBackend(self.config.get('arango_config', {}))

        else:  # auto-detect
            # Check if ArangoDB is configured and available
            if HAS_ARANGO and self._check_arango_available():
                try:
                    return ArangoBackend(self.config.get('arango_config', {}))
                except Exception as e:
                    logger.warning(f"ArangoDB initialization failed: {e}, falling back to SQLite")

            # Default to SQLite
            return SQLiteBackend(self.config.get('sqlite_path', 'youtube_transcripts.db'))

    def _check_arango_available(self) -> bool:
        """Check if ArangoDB is running and accessible"""
        if not HAS_ARANGO:
            return False

        try:
            # Try to connect to ArangoDB
            config = self.config.get('arango_config', {})
            client = ArangoClient(hosts=config.get('host', 'http://localhost:8529'))
            sys_db = client.db(
                '_system',
                username=config.get('username', 'root'),
                password=config.get('password', '')
            )
            # Check if we can access system DB
            sys_db.version()
            return True
        except:
            return False

    # Delegate all methods to the backend
    async def search(self, query: str, limit: int = 10,
                    filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Search for transcripts"""
        return await self.backend.search(query, limit, filters)

    async def store_transcript(self, video_data: dict[str, Any]) -> str:
        """Store a transcript"""
        return await self.backend.store_transcript(video_data)

    async def get_transcript(self, video_id: str) -> dict[str, Any] | None:
        """Retrieve a transcript by ID"""
        return await self.backend.get_transcript(video_id)

    async def find_evidence(self, claim: str, evidence_type: str = "both") -> list[dict[str, Any]]:
        """Find evidence for claims"""
        return await self.backend.find_evidence(claim, evidence_type)

    async def find_related(self, video_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find related videos"""
        return await self.backend.find_related(video_id, limit)

    @property
    def backend_type(self) -> str:
        """Get the type of backend being used"""
        return type(self.backend).__name__

    @property
    def has_advanced_features(self) -> bool:
        """Check if advanced features (graph, embeddings) are available"""
        return isinstance(self.backend, ArangoBackend)


# Example usage
async def example_usage():
    """Example of using the database adapter"""

    # Auto-detect backend
    db = DatabaseAdapter()
    print(f"Using backend: {db.backend_type}")
    print(f"Advanced features available: {db.has_advanced_features}")

    # Store a transcript
    video_data = {
        'video_id': 'test123',
        'title': 'Introduction to Transformers',
        'channel_name': 'AI Academy',
        'transcript': 'Transformers are a type of neural network...',
        'upload_date': '2024-01-15',
        'citations': [
            {
                'type': 'arxiv',
                'id': '1706.03762',
                'text': 'Attention Is All You Need'
            }
        ]
    }

    doc_id = await db.store_transcript(video_data)
    print(f"Stored transcript: {doc_id}")

    # Search
    results = await db.search("transformers")
    print(f"Found {len(results)} results")

    # Find evidence (works differently based on backend)
    evidence = await db.find_evidence("Transformers are better than RNNs")
    print(f"Found {len(evidence)} pieces of evidence")

    # Force SQLite backend
    sqlite_db = DatabaseAdapter({'backend': 'sqlite'})
    print(f"SQLite backend: {sqlite_db.backend_type}")

    # Force ArangoDB backend (if available)
    if HAS_ARANGO:
        arango_db = DatabaseAdapter({'backend': 'arangodb'})
        print(f"ArangoDB backend: {arango_db.backend_type}")


if __name__ == "__main__":
    asyncio.run(example_usage())
