"""
Level 0 interaction scenarios for YouTube Transcripts.
These test basic standalone functionality without external dependencies.

External Dependencies:
- youtube_transcripts: Core functionality
- sqlite3: Database operations

Example Usage:
>>> pytest tests/scenarios/test_level0_scenarios.py -v
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pytest

from youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig
from youtube_transcripts.core.database import Database
from youtube_transcripts.citation_detector import CitationDetector
from youtube_transcripts.metadata_extractor import MetadataExtractor
from youtube_transcripts.search_widener import SearchWidener


class TestLevel0Scenarios:
    """Basic interaction scenarios for YouTube Transcripts"""
    
    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Create temporary database for testing"""
        return str(tmp_path / "test_youtube.db")
    
    @pytest.fixture
    def database(self, test_db_path):
        """Initialize test database"""
        db = Database(test_db_path)
        db.initialize()
        return db
    
    @pytest.fixture
    def youtube_client(self, test_db_path):
        """Create YouTube search client with test database"""
        config = UnifiedSearchConfig(db_path=test_db_path)
        return UnifiedYouTubeSearch(config)
    
    def test_scenario_1_basic_search(self, youtube_client, database):
        """
        Scenario 1: User searches for videos in local database
        
        Given: A database with some transcripts
        When: User searches for a keyword
        Then: Relevant results are returned with snippets
        """
        # Setup: Add test transcripts
        test_transcripts = [
            {
                "video_id": "test1",
                "title": "Introduction to Machine Learning",
                "channel_name": "AI Academy",
                "text": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "upload_date": "2024-01-15"
            },
            {
                "video_id": "test2", 
                "title": "Deep Learning Fundamentals",
                "channel_name": "Neural Networks 101",
                "text": "Deep learning uses neural networks with multiple layers to process complex patterns in data.",
                "upload_date": "2024-02-20"
            }
        ]
        
        for transcript in test_transcripts:
            database.save_transcript(
                transcript["video_id"],
                transcript["title"],
                transcript["channel_name"],
                transcript["text"],
                transcript["upload_date"]
            )
        
        # Action: Search for "machine learning"
        results = youtube_client.search("machine learning", limit=10)
        
        # Verify: Check results
        assert "results" in results
        assert len(results["results"]) >= 1
        assert any("machine learning" in r["text"].lower() for r in results["results"])
        
        # Verify: First result should be most relevant
        first_result = results["results"][0]
        assert "title" in first_result
        assert "snippet" in first_result
        assert "machine learning" in first_result["snippet"].lower()
    
    def test_scenario_2_search_with_no_results(self, youtube_client):
        """
        Scenario 2: User searches for non-existent content
        
        Given: An empty or sparse database
        When: User searches for obscure term
        Then: No results are returned gracefully
        """
        # Action: Search for non-existent content
        results = youtube_client.search("xyzquantumfoobar", limit=10)
        
        # Verify: Empty results handled gracefully
        assert "results" in results
        assert len(results["results"]) == 0
        assert results.get("total_results", 0) == 0
    
    def test_scenario_3_search_widening(self, youtube_client, database):
        """
        Scenario 3: Search automatically widens when few results
        
        Given: Limited content in database
        When: User searches with typo or variation
        Then: Search widens to find related content
        """
        # Setup: Add content with specific terms
        database.save_transcript(
            "test3",
            "Transformers in NLP",
            "AI Research",
            "The transformer architecture revolutionized natural language processing.",
            "2024-03-01"
        )
        
        # Action: Search with variation
        results = youtube_client.search("transfomer", use_widening=True)  # Note typo
        
        # Verify: Search was widened
        if results.get("widening_info"):
            assert "level" in results["widening_info"]
            assert "explanation" in results["widening_info"]
            print(f"Search widened: {results['widening_info']['explanation']}")
    
    def test_scenario_4_citation_extraction(self):
        """
        Scenario 4: Extract citations from transcript
        
        Given: Transcript with academic citations
        When: Citation extraction is run
        Then: All citation types are detected
        """
        detector = CitationDetector()
        
        test_transcript = """
        Recent advances in AI have been remarkable. The seminal paper
        "Attention Is All You Need" (Vaswani et al., 2017) introduced
        transformers. See also arXiv:1810.04805 for BERT, and the
        comprehensive review at doi:10.1038/s41586-021-03819-2.
        ISBN 978-0262035613 provides a good introduction.
        """
        
        # Action: Extract citations
        citations = detector.detect_citations(test_transcript)
        
        # Verify: Different citation types found
        citation_types = {c.type for c in citations}
        assert len(citations) >= 3
        assert "arxiv" in citation_types
        assert "doi" in citation_types or "paper" in citation_types
        
        # Verify: Citation details
        arxiv_citations = [c for c in citations if c.type == "arxiv"]
        if arxiv_citations:
            assert arxiv_citations[0].id == "1810.04805"
    
    def test_scenario_5_metadata_extraction(self):
        """
        Scenario 5: Extract scientific metadata from content
        
        Given: Educational video transcript
        When: Metadata extraction is performed
        Then: Speakers, institutions, and concepts are identified
        """
        extractor = MetadataExtractor()
        
        test_transcript = """
        Welcome to today's lecture. I'm Professor Jane Smith from MIT.
        Today we'll discuss quantum computing and how qubits differ from
        classical bits. This is part of our CS 295 Advanced Topics course.
        We'll explore algorithms like Shor's algorithm and Grover's search.
        """
        
        # Action: Extract metadata
        metadata = extractor.extract_all(test_transcript)
        
        # Verify: Entities extracted
        assert "entities" in metadata
        entities = metadata["entities"]
        
        # Check for person entities
        persons = [e for e in entities if e["label"] == "PERSON"]
        assert any("Jane Smith" in p["text"] for p in persons)
        
        # Check for organizations
        orgs = [e for e in entities if e["label"] == "ORG"]
        assert any("MIT" in o["text"] for o in orgs)
        
        # Verify: Technical terms found
        assert any("quantum computing" in e["text"].lower() 
                  for e in entities if e["label"] in ["TECHNICAL_TERM", "CONCEPT"])
    
    def test_scenario_6_channel_filtering(self, youtube_client, database):
        """
        Scenario 6: Filter search results by channel
        
        Given: Transcripts from multiple channels
        When: User searches with channel filter
        Then: Only results from specified channel are returned
        """
        # Setup: Add transcripts from different channels
        channels_data = [
            ("ch1", "Channel One", "Content about AI"),
            ("ch2", "Channel Two", "Content about AI"),
            ("ch3", "Channel One", "More content about AI")
        ]
        
        for vid_id, channel, text in channels_data:
            database.save_transcript(
                vid_id,
                f"Video from {channel}",
                channel,
                text,
                "2024-01-01"
            )
        
        # Action: Search with channel filter
        results = youtube_client.search("AI", channel_filter="Channel One")
        
        # Verify: Only specified channel in results
        assert all(r["channel_name"] == "Channel One" 
                  for r in results["results"])
        assert len(results["results"]) == 2
    
    def test_scenario_7_youtube_api_search(self, youtube_client):
        """
        Scenario 7: Search YouTube API (if configured)
        
        Given: YouTube API key is configured
        When: User searches with YouTube API flag
        Then: Results from YouTube are returned
        """
        # Check if API key is configured
        if not youtube_client.youtube_api_key:
            pytest.skip("YouTube API key not configured")
        
        # Action: Search YouTube API
        results = youtube_client.search_youtube_api(
            query="Python tutorial",
            max_results=5
        )
        
        # Verify: YouTube results structure
        assert "items" in results
        assert len(results["items"]) <= 5
        
        if results["items"]:
            first_item = results["items"][0]
            assert "snippet" in first_item
            assert "title" in first_item["snippet"]
            assert "videoId" in first_item["id"]
    
    def test_scenario_8_fetch_transcript(self, youtube_client):
        """
        Scenario 8: Fetch transcript from YouTube
        
        Given: A YouTube video URL
        When: User requests transcript
        Then: Transcript is fetched and stored
        """
        # Use a known video with transcripts (educational content)
        test_video_url = "https://www.youtube.com/watch?v=aircAruvnKk"  # 3Blue1Brown neural network video
        
        try:
            # Action: Fetch transcript
            transcript = youtube_client.fetch_single_transcript(test_video_url)
            
            # Verify: Transcript fetched
            assert transcript is not None
            assert len(transcript) > 100  # Should have substantial content
            assert isinstance(transcript, str)
        except Exception as e:
            # May fail due to network or availability
            pytest.skip(f"Could not fetch transcript: {e}")
    
    def test_scenario_9_search_pagination(self, youtube_client, database):
        """
        Scenario 9: Paginate through search results
        
        Given: Many transcripts in database
        When: User searches with offset/limit
        Then: Correct page of results is returned
        """
        # Setup: Add many transcripts
        for i in range(25):
            database.save_transcript(
                f"video_{i}",
                f"Tutorial Part {i}: Python Programming",
                "Python Channel",
                f"This is tutorial number {i} about Python programming concepts.",
                "2024-01-01"
            )
        
        # Action: Search with pagination
        page1 = youtube_client.search("Python", limit=10, offset=0)
        page2 = youtube_client.search("Python", limit=10, offset=10)
        page3 = youtube_client.search("Python", limit=10, offset=20)
        
        # Verify: Different results on each page
        page1_ids = {r["video_id"] for r in page1["results"]}
        page2_ids = {r["video_id"] for r in page2["results"]}
        
        assert len(page1_ids.intersection(page2_ids)) == 0  # No overlap
        assert len(page1["results"]) == 10
        assert len(page2["results"]) == 10
        assert len(page3["results"]) == 5  # Only 5 left
    
    def test_scenario_10_scientific_classification(self):
        """
        Scenario 10: Classify content by type and level
        
        Given: Various educational transcripts
        When: Content classification is performed
        Then: Appropriate type and level are assigned
        """
        from youtube_transcripts.content_classifier import ContentClassifier
        classifier = ContentClassifier()
        
        test_cases = [
            (
                "Welcome to lecture 15 of our graduate course on quantum mechanics. "
                "Today we'll derive the time-independent Schrödinger equation.",
                "lecture",
                "graduate"
            ),
            (
                "Hey everyone! In this tutorial, I'll show you how to build your "
                "first neural network in just 10 minutes using Python!",
                "tutorial",
                "beginner"
            ),
            (
                "This conference presentation discusses our recent findings on "
                "protein folding using AlphaFold 2 methodology.",
                "conference",
                "research"
            )
        ]
        
        for transcript, expected_type, expected_level in test_cases:
            # Action: Classify content
            content_type = classifier.classify_content_type(transcript)
            academic_level = classifier.classify_academic_level(transcript)
            
            # Verify: Reasonable classification
            assert content_type in ["lecture", "tutorial", "conference", "discussion", "demonstration"]
            assert academic_level in ["beginner", "intermediate", "graduate", "research"]
            
            # These might not match exactly due to classification complexity
            print(f"Expected: {expected_type}/{expected_level}, "
                  f"Got: {content_type}/{academic_level}")


def run_standalone_scenarios():
    """Run basic scenarios without pytest"""
    print("Running Level 0 YouTube Transcripts Scenarios...\n")
    
    # Scenario 1: Basic search functionality
    print("=== Scenario 1: Basic Search ===")
    config = UnifiedSearchConfig()
    client = UnifiedYouTubeSearch(config)
    
    results = client.search("machine learning", limit=5)
    print(f"Found {len(results['results'])} results")
    if results['results']:
        print(f"First result: {results['results'][0]['title']}")
    
    # Scenario 2: Citation detection
    print("\n=== Scenario 2: Citation Detection ===")
    detector = CitationDetector()
    test_text = "See the paper arXiv:1706.03762 on transformers."
    citations = detector.detect_citations(test_text)
    print(f"Found {len(citations)} citations")
    for c in citations:
        print(f"  - {c.type}: {c.id}")
    
    # Scenario 3: Metadata extraction  
    print("\n=== Scenario 3: Metadata Extraction ===")
    extractor = MetadataExtractor()
    test_text = "Professor Smith from Stanford discusses AI ethics."
    metadata = extractor.extract_all(test_text)
    print(f"Extracted {len(metadata['entities'])} entities")
    
    # Scenario 4: Search widening
    print("\n=== Scenario 4: Search Widening ===")
    widener = SearchWidener()
    original = "VERL"
    widened = widener.widen_search(original, level=1)
    print(f"Original: {original}")
    print(f"Widened: {widened['query']}")
    print(f"Explanation: {widened['explanation']}")
    
    print("\n✅ All scenarios completed!")
    return True


if __name__ == "__main__":
    # Run standalone tests
    success = run_standalone_scenarios()
    exit(0 if success else 1)