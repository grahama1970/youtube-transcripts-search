"""
Test configuration for scenario tests with proper database isolation.
"""
import os
import pytest
import tempfile
from pathlib import Path

from youtube_transcripts.database_config import DatabaseConfig, SQLiteConfig, set_database_config
from youtube_transcripts.core.database import initialize_database


@pytest.fixture(scope="function")
def isolated_test_db():
    """Create an isolated test database for each test function."""
    # Create a unique temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    # Initialize the test database
    initialize_database(test_db_path)
    
    # Configure the system to use this test database
    test_config = DatabaseConfig(
        backend="sqlite",
        sqlite=SQLiteConfig(db_path=test_db_path),
        enable_embeddings=False,  # Disable for faster tests
        enable_graph_features=False,
        enable_research_features=False
    )
    
    # Set the test configuration globally
    set_database_config(test_config)
    original_config = None  # We'll handle restoration differently
    
    # Also set environment variable for any code that reads it directly
    original_db_path = os.environ.get("YOUTUBE_SQLITE_PATH")
    os.environ["YOUTUBE_SQLITE_PATH"] = test_db_path
    
    yield test_db_path
    
    # Cleanup: restore original configuration
    if original_config:
        set_database_config(original_config)
    
    if original_db_path:
        os.environ["YOUTUBE_SQLITE_PATH"] = original_db_path
    else:
        os.environ.pop("YOUTUBE_SQLITE_PATH", None)
    
    # Remove test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture(autouse=True)
def ensure_test_isolation(monkeypatch, isolated_test_db):
    """Automatically ensure all tests use isolated database."""
    # Patch all possible database path references
    monkeypatch.setattr('youtube_transcripts.core.database.DB_PATH', isolated_test_db)
    monkeypatch.setattr('youtube_transcripts.core.database_v2.DB_PATH', isolated_test_db, raising=False)
    
    # Patch search_transcripts to always use test database
    from youtube_transcripts.core.database import search_transcripts as original_search
    
    def mock_search_transcripts(query, channel_names=None, limit=10, db_path=None):
        # Always use the test database path
        return original_search(query, channel_names, limit, isolated_test_db)
    
    monkeypatch.setattr('youtube_transcripts.core.database.search_transcripts', mock_search_transcripts)
    monkeypatch.setattr('youtube_transcripts.unified_search.search_transcripts', mock_search_transcripts)
    
    # Patch SearchWidener to use test database
    def mock_search_widener_init(self):
        self.db_path = isolated_test_db
        self.synonym_map = {
            'ML': ['machine learning', 'ML'],
            'DL': ['deep learning', 'DL'],
            'AI': ['artificial intelligence', 'AI'],
            'NLP': ['natural language processing', 'NLP']
        }
    
    monkeypatch.setattr('youtube_transcripts.search_widener.SearchWidener.__init__', mock_search_widener_init)