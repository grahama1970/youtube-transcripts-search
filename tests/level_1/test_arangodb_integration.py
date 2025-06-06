#!/usr/bin/env python3
"""
Module: test_arangodb_integration.py
Description: Level 1 integration tests for ArangoDB - real database operations

External Dependencies:
- pytest: https://docs.pytest.org/
- python-arango: https://python-arango.readthedocs.io/

Sample Input:
>>> pytest test_arangodb_integration.py -v

Expected Output:
>>> All tests pass with real database operations

Example Usage:
>>> pytest test_arangodb_integration.py::test_connection_auth -v
"""

import time
import pytest
from arango import ArangoClient
from arango.exceptions import DatabaseCreateError, CollectionCreateError
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestArangoDBIntegration:
    """Level 1 integration tests for ArangoDB functionality."""
    
    @pytest.fixture
    def arango_client(self):
        """Create ArangoDB client."""
        return ArangoClient(hosts='http://localhost:8529')
    
    @pytest.fixture
    def test_db_name(self):
        """Test database name."""
        return 'youtube_test_db'
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_connection_auth(self, arango_client):
        """Test connecting to ArangoDB with authentication."""
        start = time.time()
        
        # Connect to system database
        sys_db = arango_client.db('_system', username='root', password='openSesame')
        
        # Verify connection by getting version
        version = sys_db.version()
        assert version is not None
        assert isinstance(version, str) and len(version) > 0
        
        # List databases (real operation)
        databases = sys_db.databases()
        assert isinstance(databases, list)
        assert '_system' in databases
        
        duration = time.time() - start
        assert duration > 0.1, f"Too fast for real DB operation: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_database_operations(self, arango_client, test_db_name):
        """Test creating and managing databases."""
        start = time.time()
        
        sys_db = arango_client.db('_system', username='root', password='openSesame')
        
        # Clean up if exists
        if sys_db.has_database(test_db_name):
            sys_db.delete_database(test_db_name)
            time.sleep(0.1)  # Allow deletion to complete
        
        # Create test database
        sys_db.create_database(test_db_name)
        assert sys_db.has_database(test_db_name)
        
        # Connect to test database
        test_db = arango_client.db(test_db_name, username='root', password='openSesame')
        
        # Verify we're connected to right DB
        db_name = test_db.name
        assert db_name == test_db_name
        
        # Clean up
        sys_db.delete_database(test_db_name)
        
        duration = time.time() - start
        assert duration > 0.2, f"Too fast for DB create/delete: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_collection_operations(self, arango_client, test_db_name):
        """Test creating and managing collections."""
        start = time.time()
        
        sys_db = arango_client.db('_system', username='root', password='openSesame')
        
        # Ensure test database exists
        if not sys_db.has_database(test_db_name):
            sys_db.create_database(test_db_name)
        
        test_db = arango_client.db(test_db_name, username='root', password='openSesame')
        
        # Create collections
        collections = ['videos', 'transcripts', 'links']
        
        for coll_name in collections:
            if test_db.has_collection(coll_name):
                test_db.delete_collection(coll_name)
            
            collection = test_db.create_collection(coll_name)
            assert collection.name == coll_name
            assert test_db.has_collection(coll_name)
            time.sleep(0.05)  # Small delay between operations
        
        # List collections
        all_collections = [c['name'] for c in test_db.collections()]
        for coll_name in collections:
            assert coll_name in all_collections
        
        # Clean up
        sys_db.delete_database(test_db_name)
        
        duration = time.time() - start
        assert duration > 0.3, f"Too fast for collection operations: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_document_operations(self, arango_client, test_db_name):
        """Test inserting and querying documents."""
        start = time.time()
        
        sys_db = arango_client.db('_system', username='root', password='openSesame')
        
        # Setup test database
        if not sys_db.has_database(test_db_name):
            sys_db.create_database(test_db_name)
        
        test_db = arango_client.db(test_db_name, username='root', password='openSesame')
        
        # Create collection
        if test_db.has_collection('videos'):
            test_db.delete_collection('videos')
        videos = test_db.create_collection('videos')
        
        # Insert documents
        test_videos = [
            {
                'video_id': 'dQw4w9WgXcQ',
                'title': 'Never Gonna Give You Up',
                'channel': 'Rick Astley',
                'duration': 'PT3M33S',
                'timestamp': time.time()
            },
            {
                'video_id': '9bZkp7q19f0',
                'title': 'Gangnam Style',
                'channel': 'Psy',
                'duration': 'PT4M12S',
                'timestamp': time.time()
            }
        ]
        
        inserted_docs = []
        for doc in test_videos:
            result = videos.insert(doc)
            assert '_id' in result
            assert '_key' in result
            inserted_docs.append(result)
            time.sleep(0.05)
        
        # Query documents
        cursor = test_db.aql.execute(
            'FOR v IN videos RETURN v',
            count=True
        )
        results = list(cursor)
        assert len(results) == 2
        
        # Query specific document
        cursor = test_db.aql.execute(
            'FOR v IN videos FILTER v.video_id == @video_id RETURN v',
            bind_vars={'video_id': 'dQw4w9WgXcQ'}
        )
        results = list(cursor)
        assert len(results) == 1
        assert results[0]['title'] == 'Never Gonna Give You Up'
        
        # Clean up
        sys_db.delete_database(test_db_name)
        
        duration = time.time() - start
        assert duration > 0.3, f"Too fast for document operations: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_error_handling(self, arango_client):
        """Test error handling for invalid operations."""
        start = time.time()
        
        # Test invalid authentication
        try:
            bad_db = arango_client.db('_system', username='root', password='wrong_password')
            bad_db.version()
            assert False, "Should have failed with bad password"
        except Exception as e:
            assert 'auth' in str(e).lower() or 'password' in str(e).lower()
        
        # Test non-existent database
        try:
            bad_db = arango_client.db('non_existent_db', username='root', password='openSesame')
            bad_db.collections()
            assert False, "Should have failed with non-existent database"
        except Exception as e:
            assert 'database' in str(e).lower()
        
        duration = time.time() - start
        assert duration > 0.1, f"Too fast: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_research_database(self, arango_client):
        """Test that research database exists and has expected structure."""
        start = time.time()
        
        sys_db = arango_client.db('_system', username='root', password='openSesame')
        
        # Check if research database exists
        has_research = sys_db.has_database('research')
        assert has_research, "Research database should exist from preparation"
        
        # Connect to research database
        research_db = arango_client.db('research', username='root', password='openSesame')
        
        # Check expected collections
        expected_collections = ['videos', 'papers', 'repositories', 'researchers']
        existing_collections = [c['name'] for c in research_db.collections()]
        
        for coll in expected_collections:
            if coll not in existing_collections:
                # Create if missing
                research_db.create_collection(coll)
        
        duration = time.time() - start
        assert duration > 0.1, f"Too fast: {duration}s"


if __name__ == "__main__":
    # Validation
    print("Running ArangoDB integration test validation...")
    
    try:
        client = ArangoClient(hosts='http://localhost:8529')
        sys_db = client.db('_system', username='root', password='openSesame')
        version = sys_db.version()
        print(f"✅ ArangoDB connected - version {version}")
        
        if sys_db.has_database('research'):
            print("✅ Research database exists")
        else:
            print("⚠️  Research database missing - will be created during tests")
            
    except Exception as e:
        print(f"❌ ArangoDB connection failed: {e}")
        print("Make sure ArangoDB is running: docker-compose up -d arangodb")
    
    print("\nRun full tests with: pytest test_arangodb_integration.py -v")