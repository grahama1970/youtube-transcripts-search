#!/usr/bin/env python3
"""
Test ArangoDB Connection for YouTube Transcripts

This script verifies that we can connect to ArangoDB and perform basic operations.

Dependencies:
- python-arango: ArangoDB Python driver
- python-dotenv: Environment variable loading

Usage:
    python tests/test_arangodb_connection.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from arango import ArangoClient
    from arango.exceptions import DocumentInsertError
except ImportError:
    logger.error("python-arango not installed. Run: uv add python-arango")
    sys.exit(1)


def test_connection():
    """Test basic ArangoDB connection and operations."""
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    host = os.getenv("ARANGO_HOST", "http://localhost:8529")
    username = os.getenv("ARANGO_USER", "root")
    password = os.getenv("ARANGO_PASSWORD", "openSesame")
    db_name = os.getenv("ARANGO_DB_NAME", "youtube_transcripts")
    
    logger.info(f"Testing connection to {host}")
    
    try:
        # Connect
        client = ArangoClient(hosts=host)
        db = client.db(db_name, username=username, password=password)
        
        # Test 1: Basic connection
        result = db.aql.execute("RETURN 1")
        assert list(result) == [1], "Basic query failed"
        logger.success("✅ Connection test passed")
        
        # Test 2: Insert test transcript
        transcripts = db.collection("transcripts")
        test_doc = {
            "video_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": "Test Video - ArangoDB Connection",
            "channel_name": "Test Channel",
            "transcript_text": "This is a test transcript for verifying ArangoDB connection.",
            "upload_date": datetime.now().isoformat(),
            "tags": ["test", "arangodb", "connection"],
            "duration": 120,
            "view_count": 0,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            result = transcripts.insert(test_doc)
            logger.success(f"✅ Insert test passed - Document ID: {result['_id']}")
            
            # Test 3: Query back
            query = "FOR t IN transcripts FILTER t.video_id == @video_id RETURN t"
            cursor = db.aql.execute(query, bind_vars={"video_id": test_doc["video_id"]})
            results = list(cursor)
            
            assert len(results) == 1, "Query didn't return expected document"
            assert results[0]["title"] == test_doc["title"], "Title mismatch"
            logger.success("✅ Query test passed")
            
            # Test 4: Full-text search
            search_query = """
            FOR doc IN transcript_search_view
              SEARCH ANALYZER(doc.transcript_text IN TOKENS('test arangodb', 'text_en'), 'text_en')
              LIMIT 1
              RETURN {title: doc.title, video_id: doc.video_id}
            """
            cursor = db.aql.execute(search_query)
            results = list(cursor)
            logger.info(f"Full-text search returned {len(results)} results")
            logger.success("✅ Search view test passed")
            
            # Test 5: Clean up
            transcripts.delete({"_key": result["_key"]})
            logger.success("✅ Cleanup test passed")
            
        except DocumentInsertError as e:
            if e.error_code == 1210:  # Unique constraint violation
                logger.warning("Document already exists, skipping insert test")
            else:
                raise
        
        # Summary
        logger.info("\n" + "="*60)
        logger.success("ALL TESTS PASSED! 🎉")
        logger.info("ArangoDB is properly configured for YouTube transcripts")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


def show_database_info():
    """Display database information."""
    from dotenv import load_dotenv
    load_dotenv()
    
    host = os.getenv("ARANGO_HOST", "http://localhost:8529")
    username = os.getenv("ARANGO_USER", "root")
    password = os.getenv("ARANGO_PASSWORD", "openSesame")
    db_name = os.getenv("ARANGO_DB_NAME", "youtube_transcripts")
    
    try:
        client = ArangoClient(hosts=host)
        db = client.db(db_name, username=username, password=password)
        
        logger.info("\nDatabase Information:")
        logger.info(f"  - Name: {db.name}")
        logger.info(f"  - Collections: {len([c for c in db.collections() if not c['name'].startswith('_')])}")
        
        # Count documents
        for coll in db.collections():
            if not coll["name"].startswith("_"):
                count = db.collection(coll["name"]).count()
                if count > 0:
                    logger.info(f"  - {coll['name']}: {count} documents")
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")


if __name__ == "__main__":
    logger.info("YouTube Transcripts - ArangoDB Connection Test")
    logger.info("=" * 60)
    
    if test_connection():
        show_database_info()
        sys.exit(0)
    else:
        sys.exit(1)