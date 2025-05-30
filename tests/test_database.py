#!/usr/bin/env python3
"""
Real tests for database functionality with actual data and proper reporting
Following CLAUDE.md: NO MOCKING, REAL DATA, PROPER REPORTS
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
import json

from youtube_transcripts.core.database import (
    initialize_database,
    add_transcript,
    search_transcripts,
    cleanup_old_transcripts
)


class TestDatabaseOperations:
    """Test database operations with real data"""
    
    @pytest.fixture
    def test_db(self):
        """Create a temporary test database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        # Initialize the database
        initialize_database(db_path)
        yield db_path
        
        # Cleanup
        db_path.unlink(missing_ok=True)
    
    def test_initialize_database_creates_tables(self, test_db):
        """Test that initialize_database creates the correct FTS5 table"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Check if transcripts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcripts'")
        result = cursor.fetchone()
        
        assert result is not None, "transcripts table was not created"
        assert result[0] == 'transcripts', f"Expected 'transcripts' table, got {result[0]}"
        
        # Verify it's an FTS5 table
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='transcripts'")
        create_sql = cursor.fetchone()[0]
        assert 'fts5' in create_sql.lower(), "Table is not using FTS5"
        
        conn.close()
    
    def test_add_transcript_with_real_data(self, test_db):
        """Test adding a real transcript to the database"""
        # Real data that might come from YouTube
        test_data = {
            "video_id": "dQw4w9WgXcQ",
            "title": "Real Video Title with Special Characters: What's Next?",
            "channel_name": "TestChannel",
            "publish_date": "2025-05-28",
            "transcript": "This is a real transcript with actual content. It includes technical terms like VERL, machine learning, and reinforcement learning.",
            "summary": "A test video about ML topics"
        }
        
        # Add the transcript
        add_transcript(
            video_id=test_data["video_id"],
            title=test_data["title"],
            channel_name=test_data["channel_name"],
            publish_date=test_data["publish_date"],
            transcript=test_data["transcript"],
            summary=test_data["summary"],
            db_path=test_db
        )
        
        # Verify it was added
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transcripts WHERE video_id = ?", (test_data["video_id"],))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "Transcript was not added to database"
        assert test_data["video_id"] in result, f"Video ID not found in result: {result}"
        assert test_data["title"] in result, f"Title not found in result: {result}"
    
    def test_search_transcripts_with_special_characters(self, test_db):
        """Test searching with queries containing special characters"""
        # Add test data
        test_transcripts = [
            {
                "video_id": "test1",
                "title": "How does VERL work?",
                "channel_name": "MLChannel",
                "publish_date": "2025-05-28",
                "transcript": "VERL stands for Volcano Engine Reinforcement Learning. It's a framework for training models.",
                "summary": ""
            },
            {
                "video_id": "test2",
                "title": "Machine Learning Basics!",
                "channel_name": "MLChannel",
                "publish_date": "2025-05-27",
                "transcript": "Let's learn about neural networks and deep learning.",
                "summary": ""
            }
        ]
        
        for transcript in test_transcripts:
            add_transcript(**transcript, db_path=test_db)
        
        # Test search with special characters (should not crash)
        queries_to_test = [
            "VERL?",
            "How does it work?",
            "Machine Learning!",
            "neural networks: basics"
        ]
        
        for query in queries_to_test:
            results = search_transcripts(query, db_path=test_db)
            # Should not raise an exception
            assert isinstance(results, list), f"Search returned non-list for query: {query}"
    
    def test_search_ranking_with_real_data(self, test_db):
        """Test that BM25 ranking works correctly"""
        # Add documents with varying relevance
        docs = [
            {
                "video_id": "low_relevance",
                "title": "Random Video",
                "channel_name": "Random",
                "publish_date": "2025-05-01",
                "transcript": "This video mentions reinforcement once.",
                "summary": ""
            },
            {
                "video_id": "high_relevance",
                "title": "Reinforcement Learning Deep Dive",
                "channel_name": "ML Expert",
                "publish_date": "2025-05-01",
                "transcript": "Reinforcement learning is mentioned many times. Reinforcement learning algorithms. Reinforcement learning applications.",
                "summary": "All about reinforcement learning"
            }
        ]
        
        for doc in docs:
            add_transcript(**doc, db_path=test_db)
        
        # Search for "reinforcement learning"
        results = search_transcripts("reinforcement learning", db_path=test_db)
        
        assert len(results) >= 2, f"Expected at least 2 results, got {len(results)}"
        
        # Check if high relevance document ranks higher
        if len(results) >= 2:
            # Find the positions of our test documents
            positions = {}
            for i, result in enumerate(results):
                if result['video_id'] in ['high_relevance', 'low_relevance']:
                    positions[result['video_id']] = i
            
            if 'high_relevance' in positions and 'low_relevance' in positions:
                assert positions['high_relevance'] < positions['low_relevance'], \
                    "High relevance document should rank higher than low relevance"
    
    def test_channel_filtering(self, test_db):
        """Test filtering results by channel"""
        # Add transcripts from different channels
        channels_data = [
            ("video1", "Channel A Video", "ChannelA", "2025-05-01", "Content about Python"),
            ("video2", "Channel B Video", "ChannelB", "2025-05-01", "Content about Python"),
            ("video3", "Another Channel A", "ChannelA", "2025-05-01", "More Python content"),
        ]
        
        for video_id, title, channel, date, transcript in channels_data:
            add_transcript(video_id, title, channel, date, transcript, db_path=test_db)
        
        # Search with channel filter
        results = search_transcripts("Python", channel_names=["ChannelA"], db_path=test_db)
        
        # Verify only ChannelA results are returned
        for result in results:
            assert result['channel_name'] == "ChannelA", \
                f"Got result from wrong channel: {result['channel_name']}"
        
        # Verify we got the right number of results
        assert len(results) == 2, f"Expected 2 results from ChannelA, got {len(results)}"
    
    def test_cleanup_old_transcripts(self, test_db):
        """Test cleanup of old transcripts"""
        # Add transcripts with different dates
        old_date = "2024-01-01"  # Old
        recent_date = "2025-05-01"  # Recent
        
        add_transcript("old_video", "Old Video", "Channel", old_date, "Ancient transcript text", db_path=test_db)
        add_transcript("new_video", "New Video", "Channel", recent_date, "Modern transcript text", db_path=test_db)
        
        # Cleanup transcripts older than 3 months
        deleted_count = cleanup_old_transcripts(3, db_path=test_db)
        
        assert deleted_count == 1, f"Expected 1 transcript deleted, got {deleted_count}"
        
        # Verify old video is gone
        results = search_transcripts("Ancient", db_path=test_db)
        assert len(results) == 0, "Old transcript was not deleted"
        
        # Verify new video remains
        results = search_transcripts("Modern", db_path=test_db)
        assert len(results) == 1, "Recent transcript was incorrectly deleted"


def generate_test_report(test_results):
    """Generate a markdown report for test results"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(__file__).parent.parent / "docs" / "reports" / f"database_test_report_{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write("# Database Test Report\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n")
        f.write("**Component**: YouTube Transcripts Database\n")
        f.write("**Test Type**: Real Data Tests - No Mocking\n\n")
        
        f.write("## Test Results\n\n")
        f.write("| Test Name | Description | Status | Duration | Notes |\n")
        f.write("|-----------|-------------|--------|----------|-------|\n")
        
        # Write test results (this would be populated by pytest hooks in real implementation)
        # For now, we'll note that this should be integrated with pytest reporting
        
        f.write("\n## Summary\n\n")
        f.write("- All tests use real SQLite operations\n")
        f.write("- No mocking of database functionality\n")
        f.write("- Tests verify actual behavior with real data\n")
        
    return report_path


if __name__ == "__main__":
    # Run with pytest and generate report
    pytest.main([__file__, "-v", "--tb=short"])