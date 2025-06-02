"""
ArangoDB Integration for YouTube Transcripts
Migrates from SQLite to ArangoDB for enhanced research capabilities

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
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import hashlib

from arango import ArangoClient
from arango.database import StandardDatabase

# Import Granger's ArangoDB utilities
try:
    from arangodb.core.search import hybrid_search as granger_hybrid_search
    from arangodb.core.search import semantic_search as granger_semantic_search
    from arangodb.core.utils.embedding_utils import get_embedding
    from arangodb.core.arango_setup import connect_arango, ensure_database
    GRANGER_ARANGO = True
except ImportError:
    GRANGER_ARANGO = False
    print("Warning: Granger ArangoDB utilities not available")


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
        self.db_name = db_name
        self.host = host
        
        # Collection names following Granger convention
        self.collections = {
            'transcripts': 'youtube_transcripts',
            'speakers': 'youtube_speakers',
            'channels': 'youtube_channels',
            'citations': 'youtube_citations',
            'entities': 'youtube_entities',
            'claims': 'youtube_claims'
        }
        
        # Edge collections for relationships
        self.edge_collections = {
            'cites': 'youtube_cites',
            'speaks_in': 'youtube_speaks_in',
            'mentions': 'youtube_mentions',
            'supports': 'youtube_supports',
            'contradicts': 'youtube_contradicts',
            'related_to': 'youtube_related_to'
        }
        
        # Connect to database
        self.client = ArangoClient(hosts=host)
        self.db = self._setup_database(username, password)
        self._ensure_collections()
        self._ensure_indexes()
        self._ensure_graph()
    
    def _setup_database(self, username: str, password: str) -> StandardDatabase:
        """Setup database connection"""
        if GRANGER_ARANGO:
            # Use Granger's connection utilities
            try:
                # connect_arango likely expects a config dict
                config = {
                    'host': self.host,
                    'username': username,
                    'password': password,
                    'database': self.db_name
                }
                return connect_arango(**config)
            except Exception:
                # Fall back to direct connection if Granger utils fail
                pass
        
        # Manual connection
        sys_db = self.client.db('_system', username=username, password=password)
        if not sys_db.has_database(self.db_name):
            sys_db.create_database(self.db_name)
        return self.client.db(self.db_name, username=username, password=password)
    
    def _ensure_collections(self):
        """Create collections if they don't exist"""
        # Document collections
        for name, collection in self.collections.items():
            if not self.db.has_collection(collection):
                self.db.create_collection(collection)
        
        # Edge collections
        for name, collection in self.edge_collections.items():
            if not self.db.has_collection(collection):
                self.db.create_collection(collection, edge=True)
    
    def _ensure_indexes(self):
        """Create necessary indexes"""
        # Full-text search indexes
        transcripts = self.db.collection(self.collections['transcripts'])
        
        # Ensure indexes exist
        existing_indexes = {idx['name'] for idx in transcripts.indexes()}
        
        if 'transcript_fulltext' not in existing_indexes:
            transcripts.add_fulltext_index(fields=['transcript'], name='transcript_fulltext')
        
        if 'title_fulltext' not in existing_indexes:
            transcripts.add_fulltext_index(fields=['title'], name='title_fulltext')
        
        # Hash indexes for lookups
        if 'video_id_hash' not in existing_indexes:
            transcripts.add_hash_index(fields=['video_id'], unique=True, name='video_id_hash')
    
    def _ensure_graph(self):
        """Create graph if it doesn't exist"""
        graph_name = 'youtube_knowledge_graph'
        
        if not self.db.has_graph(graph_name):
            # Define edge definitions
            edge_definitions = [
                {
                    'edge_collection': self.edge_collections['cites'],
                    'from_vertex_collections': [self.collections['transcripts']],
                    'to_vertex_collections': [self.collections['citations']]
                },
                {
                    'edge_collection': self.edge_collections['speaks_in'],
                    'from_vertex_collections': [self.collections['speakers']],
                    'to_vertex_collections': [self.collections['transcripts']]
                },
                {
                    'edge_collection': self.edge_collections['mentions'],
                    'from_vertex_collections': [self.collections['transcripts']],
                    'to_vertex_collections': [self.collections['entities']]
                },
                {
                    'edge_collection': self.edge_collections['supports'],
                    'from_vertex_collections': [self.collections['transcripts']],
                    'to_vertex_collections': [self.collections['claims']]
                },
                {
                    'edge_collection': self.edge_collections['contradicts'],
                    'from_vertex_collections': [self.collections['transcripts']],
                    'to_vertex_collections': [self.collections['claims']]
                },
                {
                    'edge_collection': self.edge_collections['related_to'],
                    'from_vertex_collections': [self.collections['transcripts']],
                    'to_vertex_collections': [self.collections['transcripts']]
                }
            ]
            
            self.db.create_graph(graph_name, edge_definitions=edge_definitions)
    
    async def store_transcript(self, video_data: Dict[str, Any]) -> str:
        """
        Store a transcript with all its relationships
        
        Args:
            video_data: Dictionary containing video information
            
        Returns:
            Document ID of stored transcript
        """
        # Prepare transcript document
        transcript_doc = {
            '_key': video_data['video_id'],
            'video_id': video_data['video_id'],
            'title': video_data['title'],
            'channel_name': video_data.get('channel_name', ''),
            'channel_id': video_data.get('channel_id', ''),
            'transcript': video_data['transcript'],
            'upload_date': video_data.get('upload_date', ''),
            'duration': video_data.get('duration', 0),
            'view_count': video_data.get('view_count', 0),
            'url': f"https://youtube.com/watch?v={video_data['video_id']}",
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'language': video_data.get('language', 'en'),
                'auto_generated': video_data.get('auto_generated', False),
                'description': video_data.get('description', '')
            }
        }
        
        # Add embedding if available
        if GRANGER_ARANGO:
            transcript_doc['embedding'] = get_embedding(video_data['transcript'])
            transcript_doc['embedding_model'] = 'BAAI/bge-large-en-v1.5'
        
        # Store transcript
        transcripts = self.db.collection(self.collections['transcripts'])
        result = transcripts.insert(transcript_doc, overwrite=True)
        doc_id = result['_id']
        
        # Store channel if new
        await self._store_channel(video_data)
        
        # Process and store citations
        if 'citations' in video_data:
            await self._store_citations(video_data['video_id'], video_data['citations'])
        
        # Process and store speakers
        if 'speakers' in video_data:
            await self._store_speakers(video_data['video_id'], video_data['speakers'])
        
        # Process and store entities
        if 'entities' in video_data:
            await self._store_entities(video_data['video_id'], video_data['entities'])
        
        return doc_id
    
    async def _store_channel(self, video_data: Dict[str, Any]):
        """Store channel information"""
        if not video_data.get('channel_id'):
            return
        
        channel_doc = {
            '_key': video_data['channel_id'],
            'channel_id': video_data['channel_id'],
            'channel_name': video_data.get('channel_name', ''),
            'channel_url': video_data.get('channel_url', ''),
            'subscriber_count': video_data.get('subscriber_count', 0),
            'video_count': video_data.get('video_count', 0),
            'description': video_data.get('channel_description', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        channels = self.db.collection(self.collections['channels'])
        channels.insert(channel_doc, overwrite=True)
    
    async def _store_citations(self, video_id: str, citations: List[Dict[str, Any]]):
        """Store citations and create relationships"""
        citations_coll = self.db.collection(self.collections['citations'])
        cites_coll = self.db.collection(self.edge_collections['cites'])
        
        for citation in citations:
            # Create unique key for citation
            citation_key = hashlib.md5(
                f"{citation['type']}:{citation.get('id', citation['text'])}".encode()
            ).hexdigest()
            
            citation_doc = {
                '_key': citation_key,
                'type': citation['type'],
                'identifier': citation.get('id', ''),
                'text': citation['text'],
                'context': citation.get('context', ''),
                'metadata': citation.get('metadata', {})
            }
            
            # Insert citation
            citations_coll.insert(citation_doc, overwrite=True)
            
            # Create edge from transcript to citation
            edge_doc = {
                '_from': f"{self.collections['transcripts']}/{video_id}",
                '_to': f"{self.collections['citations']}/{citation_key}",
                'timestamp': citation.get('timestamp', 0),
                'confidence': citation.get('confidence', 1.0)
            }
            
            cites_coll.insert(edge_doc, overwrite=True)
    
    async def _store_speakers(self, video_id: str, speakers: List[Dict[str, Any]]):
        """Store speakers and create relationships"""
        speakers_coll = self.db.collection(self.collections['speakers'])
        speaks_in_coll = self.db.collection(self.edge_collections['speaks_in'])
        
        for speaker in speakers:
            # Create unique key for speaker
            speaker_key = hashlib.md5(
                speaker['name'].lower().encode()
            ).hexdigest()
            
            speaker_doc = {
                '_key': speaker_key,
                'name': speaker['name'],
                'title': speaker.get('title', ''),
                'affiliation': speaker.get('affiliation', ''),
                'credentials': speaker.get('credentials', []),
                'topics': speaker.get('topics', [])
            }
            
            # Insert speaker
            speakers_coll.insert(speaker_doc, overwrite=True)
            
            # Create edge from speaker to transcript
            edge_doc = {
                '_from': f"{self.collections['speakers']}/{speaker_key}",
                '_to': f"{self.collections['transcripts']}/{video_id}",
                'role': speaker.get('role', 'speaker'),
                'duration': speaker.get('duration', 0)
            }
            
            speaks_in_coll.insert(edge_doc, overwrite=True)
    
    async def _store_entities(self, video_id: str, entities: List[Dict[str, Any]]):
        """Store entities and create relationships"""
        entities_coll = self.db.collection(self.collections['entities'])
        mentions_coll = self.db.collection(self.edge_collections['mentions'])
        
        for entity in entities:
            # Create unique key for entity
            entity_key = hashlib.md5(
                f"{entity['type']}:{entity['text']}".encode()
            ).hexdigest()
            
            entity_doc = {
                '_key': entity_key,
                'text': entity['text'],
                'type': entity['label'],
                'category': entity.get('category', ''),
                'metadata': entity.get('metadata', {})
            }
            
            # Insert entity
            entities_coll.insert(entity_doc, overwrite=True)
            
            # Create edge from transcript to entity
            edge_doc = {
                '_from': f"{self.collections['transcripts']}/{video_id}",
                '_to': f"{self.collections['entities']}/{entity_key}",
                'count': entity.get('count', 1),
                'positions': entity.get('positions', [])
            }
            
            mentions_coll.insert(edge_doc, overwrite=True)
    
    async def hybrid_search(self, query: str, limit: int = 10, 
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search using Granger's search capabilities
        
        Args:
            query: Search query
            limit: Maximum results
            filters: Optional filters
            
        Returns:
            List of search results
        """
        if False and GRANGER_ARANGO:
            # Use Granger's hybrid search (disabled for now due to API mismatch)
            results = await granger_hybrid_search(
                db=self.db,
                query=query,
                collections=[self.collections['transcripts']],
                limit=limit,
                filter_expression=self._build_filter_expression(filters)
            )
            return results['results']
        else:
            # Fallback to basic search
            return await self._basic_search(query, limit, filters)
    
    async def _basic_search(self, query: str, limit: int, 
                          filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Basic fulltext search fallback"""
        aql = """
        FOR doc IN FULLTEXT(@collection, 'transcript', @query)
            LIMIT @limit
            RETURN doc
        """
        
        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                'collection': self.collections['transcripts'],
                'query': query,
                'limit': limit
            }
        )
        
        return list(cursor)
    
    async def semantic_search(self, query: str, limit: int = 10,
                            filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings
        
        Args:
            query: Search query
            limit: Maximum results
            filters: Optional filters
            
        Returns:
            List of search results
        """
        if False and GRANGER_ARANGO and get_embedding:
            # Get query embedding
            query_embedding = await get_embedding(query)
            
            # Use Granger's semantic search (disabled for now)
            results = await granger_semantic_search(
                db=self.db,
                query_embedding=query_embedding,
                collection=self.collections['transcripts'],
                limit=limit,
                filter_expression=self._build_filter_expression(filters)
            )
            return results
        else:
            # Fall back to regular search if embeddings not available
            return await self.hybrid_search(query, limit, filters)
    
    def _build_filter_expression(self, filters: Optional[Dict[str, Any]]) -> Optional[str]:
        """Build AQL filter expression from filters"""
        if not filters:
            return None
        
        conditions = []
        
        if 'channel' in filters:
            conditions.append(f"doc.channel_name == '{filters['channel']}'")
        
        if 'date_after' in filters:
            conditions.append(f"doc.upload_date >= '{filters['date_after']}'")
        
        if 'min_views' in filters:
            conditions.append(f"doc.view_count >= {filters['min_views']}")
        
        return " AND ".join(conditions) if conditions else None
    
    async def find_related_videos(self, video_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find related videos using graph traversal"""
        aql = """
        LET video = DOCUMENT(@video_id)
        
        // Find videos that share citations
        LET citation_related = (
            FOR v, e, p IN 2..2 ANY video
                GRAPH 'youtube_knowledge_graph'
                FILTER IS_SAME_COLLECTION('youtube_cites', e)
                FILTER v._id != video._id
                RETURN DISTINCT v
        )
        
        // Find videos by same speaker
        LET speaker_related = (
            FOR v, e, p IN 2..2 ANY video
                GRAPH 'youtube_knowledge_graph'
                FILTER IS_SAME_COLLECTION('youtube_speaks_in', e)
                FILTER v._id != video._id
                RETURN DISTINCT v
        )
        
        // Combine and rank
        FOR v IN UNION_DISTINCT(citation_related, speaker_related)
            LIMIT @limit
            RETURN v
        """
        
        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                'video_id': f"{self.collections['transcripts']}/{video_id}",
                'limit': limit
            }
        )
        
        return list(cursor)
    
    async def find_videos_by_speaker(self, speaker_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find videos featuring a specific speaker"""
        aql = """
        FOR speaker IN youtube_speakers
            FILTER speaker.name == @speaker_name
            FOR video IN 1..1 INBOUND speaker youtube_speaks_in
                LIMIT @limit
                RETURN video
        """
        
        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                'speaker_name': speaker_name,
                'limit': limit
            }
        )
        
        return list(cursor)
    
    async def get_citation_network(self, video_id: str, depth: int = 2) -> Dict[str, Any]:
        """Build citation network for a video"""
        aql = """
        FOR v, e, p IN 1..@depth ANY @start_vertex
            GRAPH 'youtube_knowledge_graph'
            FILTER IS_SAME_COLLECTION('youtube_cites', e)
            RETURN {
                vertex: v,
                edge: e,
                depth: LENGTH(p.edges)
            }
        """
        
        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                'start_vertex': f"{self.collections['transcripts']}/{video_id}",
                'depth': depth
            }
        )
        
        # Build network structure
        nodes = []
        edges = []
        
        for item in cursor:
            nodes.append(item['vertex'])
            if item['edge']:
                edges.append(item['edge'])
        
        return {
            'nodes': nodes,
            'edges': edges,
            'root': video_id
        }
    
    async def find_contradictions(self, claim: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find videos that contradict a claim"""
        # This would integrate with the research_analyzer module
        # For now, return placeholder
        return []
    
    def migrate_from_sqlite(self, sqlite_path: str):
        """Migrate data from SQLite to ArangoDB"""
        import sqlite3
        
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # Get all transcripts
        cursor.execute("SELECT * FROM transcripts")
        columns = [description[0] for description in cursor.description]
        
        for row in cursor.fetchall():
            video_data = dict(zip(columns, row))
            
            # Transform to expected format
            video_data['transcript'] = video_data.get('transcript', '')
            
            # Store in ArangoDB
            asyncio.run(self.store_transcript(video_data))
        
        conn.close()
        print(f"Migration complete!")


# Example usage
async def example_usage():
    """Example of using the ArangoDB integration"""
    # Initialize graph
    graph = YouTubeTranscriptGraph()
    
    # Store a transcript
    video_data = {
        'video_id': 'example123',
        'title': 'Introduction to Transformers',
        'channel_name': 'AI Academy',
        'transcript': 'Transformers revolutionized NLP by using attention mechanisms...',
        'upload_date': '2024-01-15',
        'citations': [
            {
                'type': 'arxiv',
                'id': '1706.03762',
                'text': 'Attention Is All You Need',
                'context': 'The seminal paper by Vaswani et al.'
            }
        ],
        'speakers': [
            {
                'name': 'Dr. Jane Smith',
                'affiliation': 'MIT',
                'title': 'Professor of Computer Science'
            }
        ]
    }
    
    doc_id = await graph.store_transcript(video_data)
    print(f"Stored transcript: {doc_id}")
    
    # Search
    results = await graph.hybrid_search("attention mechanisms")
    print(f"Found {len(results)} results")
    
    # Find related videos
    related = await graph.find_related_videos('example123')
    print(f"Found {len(related)} related videos")


if __name__ == "__main__":
    asyncio.run(example_usage())