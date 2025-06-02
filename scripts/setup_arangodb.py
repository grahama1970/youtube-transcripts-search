#!/usr/bin/env python3
"""
ArangoDB Setup Script for YouTube Transcripts

This script sets up ArangoDB for the YouTube transcripts project.
It creates the necessary database, collections, and indexes.

Dependencies:
- python-arango: ArangoDB Python driver
- loguru: Logging library

Usage:
    python scripts/setup_arangodb.py
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from arango import ArangoClient
    HAS_ARANGO = True
except ImportError:
    logger.error("python-arango is not installed. Install with: uv add python-arango")
    HAS_ARANGO = False
    sys.exit(1)


def setup_arangodb():
    """Set up ArangoDB for YouTube transcripts."""
    # Get configuration from environment
    host = os.getenv("ARANGO_HOST", "http://localhost:8529")
    username = os.getenv("ARANGO_USER", "root")
    password = os.getenv("ARANGO_PASSWORD", "openSesame")
    db_name = os.getenv("ARANGO_DB_NAME", "youtube_transcripts")
    
    logger.info(f"Connecting to ArangoDB at {host}")
    
    try:
        # Connect to ArangoDB
        client = ArangoClient(hosts=host)
        
        # Connect to system database
        sys_db = client.db("_system", username=username, password=password)
        
        # Create database if it doesn't exist
        if not sys_db.has_database(db_name):
            logger.info(f"Creating database: {db_name}")
            sys_db.create_database(db_name)
        else:
            logger.info(f"Database {db_name} already exists")
        
        # Connect to the YouTube transcripts database
        db = client.db(db_name, username=username, password=password)
        
        # Define collections to create
        collections = {
            # Main transcript collection
            "transcripts": {
                "type": "document",
                "schema": {
                    "video_id": "str",
                    "channel_id": "str",
                    "channel_name": "str",
                    "title": "str",
                    "description": "str",
                    "upload_date": "str",
                    "duration": "int",
                    "view_count": "int",
                    "like_count": "int",
                    "comment_count": "int",
                    "transcript_text": "str",
                    "transcript_segments": "list",
                    "language": "str",
                    "tags": "list",
                    "categories": "list",
                    "created_at": "str",
                    "updated_at": "str"
                }
            },
            
            # Transcript chunks for semantic search
            "transcript_chunks": {
                "type": "document",
                "schema": {
                    "transcript_id": "str",
                    "video_id": "str",
                    "chunk_index": "int",
                    "start_time": "float",
                    "end_time": "float",
                    "text": "str",
                    "embedding": "list",
                    "metadata": "dict"
                }
            },
            
            # Entities extracted from transcripts
            "entities": {
                "type": "document",
                "schema": {
                    "name": "str",
                    "type": "str",
                    "description": "str",
                    "aliases": "list",
                    "metadata": "dict"
                }
            },
            
            # Relationships between entities
            "entity_mentions": {
                "type": "edge",
                "schema": {
                    "_from": "str",
                    "_to": "str",
                    "mention_type": "str",
                    "context": "str",
                    "confidence": "float",
                    "timestamp": "str"
                }
            },
            
            # Search history and analytics
            "search_history": {
                "type": "document",
                "schema": {
                    "query": "str",
                    "search_type": "str",
                    "results_count": "int",
                    "clicked_results": "list",
                    "timestamp": "str",
                    "user_id": "str"
                }
            }
        }
        
        # Create collections
        for coll_name, coll_info in collections.items():
            if not db.has_collection(coll_name):
                logger.info(f"Creating collection: {coll_name}")
                if coll_info["type"] == "edge":
                    db.create_collection(coll_name, edge=True)
                else:
                    db.create_collection(coll_name)
            else:
                logger.info(f"Collection {coll_name} already exists")
        
        # Create indexes
        logger.info("Creating indexes...")
        
        # Transcripts indexes
        if db.has_collection("transcripts"):
            transcripts = db.collection("transcripts")
            
            # Ensure indexes
            indexes_to_create = [
                {"fields": ["video_id"], "unique": True, "name": "idx_video_id"},
                {"fields": ["channel_id"], "name": "idx_channel_id"},
                {"fields": ["upload_date"], "name": "idx_upload_date"},
                {"fields": ["tags[*]"], "name": "idx_tags"},
                {"fields": ["channel_name", "upload_date"], "name": "idx_channel_date"}
            ]
            
            existing_indexes = {idx["name"] for idx in transcripts.indexes() if "name" in idx}
            
            for idx_config in indexes_to_create:
                if idx_config["name"] not in existing_indexes:
                    logger.info(f"Creating index: {idx_config['name']}")
                    transcripts.add_persistent_index(**idx_config)
        
        # Transcript chunks indexes (for vector search)
        if db.has_collection("transcript_chunks"):
            chunks = db.collection("transcript_chunks")
            
            # Create indexes
            indexes_to_create = [
                {"fields": ["transcript_id"], "name": "idx_transcript_id"},
                {"fields": ["video_id"], "name": "idx_chunk_video_id"}
            ]
            
            existing_indexes = {idx["name"] for idx in chunks.indexes() if "name" in idx}
            
            for idx_config in indexes_to_create:
                if idx_config["name"] not in existing_indexes:
                    logger.info(f"Creating index: {idx_config['name']}")
                    chunks.add_persistent_index(**idx_config)
        
        # Create ArangoSearch view for full-text search
        view_name = "transcript_search_view"
        if view_name not in [v["name"] for v in db.views()]:
            logger.info(f"Creating ArangoSearch view: {view_name}")
            db.create_arangosearch_view(
                name=view_name,
                properties={
                    "links": {
                        "transcripts": {
                            "includeAllFields": False,
                            "fields": {
                                "title": {"analyzers": ["text_en", "identity"]},
                                "description": {"analyzers": ["text_en"]},
                                "transcript_text": {"analyzers": ["text_en"]},
                                "channel_name": {"analyzers": ["identity"]},
                                "tags": {"analyzers": ["identity"]}
                            }
                        },
                        "transcript_chunks": {
                            "includeAllFields": False,
                            "fields": {
                                "text": {"analyzers": ["text_en"]}
                            }
                        }
                    }
                }
            )
        
        logger.success("ArangoDB setup completed successfully!")
        
        # Test the connection
        logger.info("Testing database connection...")
        result = db.aql.execute("RETURN 1")
        logger.success("Database connection test passed!")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup ArangoDB: {e}")
        return False


def verify_setup():
    """Verify the ArangoDB setup."""
    host = os.getenv("ARANGO_HOST", "http://localhost:8529")
    username = os.getenv("ARANGO_USER", "root")
    password = os.getenv("ARANGO_PASSWORD", "openSesame")
    db_name = os.getenv("ARANGO_DB_NAME", "youtube_transcripts")
    
    try:
        client = ArangoClient(hosts=host)
        db = client.db(db_name, username=username, password=password)
        
        # Check collections
        collections = db.collections()
        logger.info(f"Found {len(collections)} collections:")
        for coll in collections:
            if not coll["name"].startswith("_"):  # Skip system collections
                logger.info(f"  - {coll['name']} (type: {coll['type']})")
        
        # Check views
        views = db.views()
        logger.info(f"Found {len(views)} views:")
        for view in views:
            logger.info(f"  - {view['name']} (type: {view['type']})")
        
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded environment variables from .env")
    
    logger.info("=" * 60)
    logger.info("YouTube Transcripts - ArangoDB Setup")
    logger.info("=" * 60)
    
    # Run setup
    if setup_arangodb():
        logger.info("\nVerifying setup...")
        verify_setup()
        logger.success("\n✅ ArangoDB is ready for YouTube transcripts!")
        logger.info("\nYou can now use the database with:")
        logger.info("  - Database: youtube_transcripts")
        logger.info("  - Collections: transcripts, transcript_chunks, entities, etc.")
        logger.info("  - Full-text search view: transcript_search_view")
    else:
        logger.error("\n❌ Setup failed. Please check the logs above.")
        sys.exit(1)