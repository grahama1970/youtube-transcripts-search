"""
ArangoDB Connection and Setup for YouTube Transcripts
Module: arango_connection.py
Description: Implementation of arango connection functionality

This module handles database connection, collection setup, and basic configuration
for the YouTube Transcripts ArangoDB integration.

External Dependencies:
- python-arango: ArangoDB Python driver
- arangodb.core: Granger's ArangoDB utilities (optional)
"""

from arango import ArangoClient
from arango.database import StandardDatabase

# Import Granger's ArangoDB utilities
try:
    from arangodb.core.arango_setup import connect_arango, ensure_database
    from arangodb.core.utils.embedding_utils import get_embedding
    GRANGER_ARANGO = True
except ImportError:
    GRANGER_ARANGO = False
    print("Warning: Granger ArangoDB utilities not available")


class ArangoConnection:
    """Manages ArangoDB connection and setup"""

    def __init__(self, db_name: str = "memory_bank",
                 host: str = "http://localhost:8529",
                 username: str = "root",
                 password: str = ""):
        """Initialize connection parameters"""
        self.db_name = db_name
        self.host = host
        self.username = username
        self.password = password
        self.client = ArangoClient(hosts=host)

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

    def connect(self) -> StandardDatabase:
        """Setup database connection"""
        if GRANGER_ARANGO:
            # Use Granger's connection utilities
            try:
                config = {
                    'host': self.host,
                    'username': self.username,
                    'password': self.password,
                    'database': self.db_name
                }
                return connect_arango(**config)
            except Exception:
                # Fall back to direct connection
                pass

        # Direct connection
        sys_db = self.client.db('_system', username=self.username, password=self.password)

        # Create database if it doesn't exist
        if not sys_db.has_database(self.db_name):
            sys_db.create_database(self.db_name)

        # Connect to the database
        return self.client.db(self.db_name, username=self.username, password=self.password)

    def ensure_collections(self, db: StandardDatabase):
        """Ensure all required collections exist"""
        # Document collections
        for name, collection in self.collections.items():
            if not db.has_collection(collection):
                db.create_collection(collection)

        # Edge collections
        for name, collection in self.edge_collections.items():
            if not db.has_collection(collection):
                db.create_collection(collection, edge=True)

    def ensure_indexes(self, db: StandardDatabase):
        """Create necessary indexes for performance"""
        # Transcript indexes
        transcripts = db.collection(self.collections['transcripts'])
        transcripts.add_persistent_index(fields=['video_id'], unique=True)
        transcripts.add_persistent_index(fields=['channel_id'])
        transcripts.add_persistent_index(fields=['fetched_at'])
        transcripts.add_fulltext_index(fields=['title'])
        transcripts.add_fulltext_index(fields=['content'])

        # Speaker indexes
        speakers = db.collection(self.collections['speakers'])
        speakers.add_persistent_index(fields=['name'])
        speakers.add_persistent_index(fields=['channel_id'])

        # Channel indexes
        channels = db.collection(self.collections['channels'])
        channels.add_persistent_index(fields=['handle'], unique=True)
        channels.add_fulltext_index(fields=['name'])

        # Citation indexes
        citations = db.collection(self.collections['citations'])
        citations.add_persistent_index(fields=['paper_title'])
        citations.add_persistent_index(fields=['arxiv_id'])
        citations.add_persistent_index(fields=['doi'])

        # Entity indexes
        entities = db.collection(self.collections['entities'])
        entities.add_persistent_index(fields=['name'])
        entities.add_persistent_index(fields=['type'])

    def ensure_graph(self, db: StandardDatabase):
        """Create graph structure for relationships"""
        graph_name = 'youtube_knowledge_graph'

        if not db.has_graph(graph_name):
            # Define graph edges
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
                    'from_vertex_collections': [self.collections['transcripts'], self.collections['claims']],
                    'to_vertex_collections': [self.collections['claims']]
                },
                {
                    'edge_collection': self.edge_collections['contradicts'],
                    'from_vertex_collections': [self.collections['transcripts'], self.collections['claims']],
                    'to_vertex_collections': [self.collections['claims']]
                },
                {
                    'edge_collection': self.edge_collections['related_to'],
                    'from_vertex_collections': [self.collections['transcripts']],
                    'to_vertex_collections': [self.collections['transcripts']]
                }
            ]

            db.create_graph(graph_name, edge_definitions=edge_definitions)
