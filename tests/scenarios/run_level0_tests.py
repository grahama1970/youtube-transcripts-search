"""
Simple runner for Level 0 interaction scenarios.
Tests basic YouTube Transcripts functionality.

Example Usage:
>>> python tests/scenarios/run_level0_tests.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig
from youtube_transcripts.citation_detector import CitationDetector
from youtube_transcripts.metadata_extractor import MetadataExtractor
from youtube_transcripts.search_widener import SearchWidener
from youtube_transcripts.core import database


class Level0TestRunner:
    """Runs basic interaction tests for YouTube Transcripts"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name, func):
        """Run a test and track results"""
        print(f"\n🧪 {name}")
        try:
            result = func()
            if result:
                print("   ✅ PASSED")
                self.passed += 1
            else:
                print("   ❌ FAILED")
                self.failed += 1
            self.tests.append((name, result))
            return result
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            self.failed += 1
            self.tests.append((name, False))
            return False
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {self.passed}/{total} passed")
        print("="*60)
        
        if self.failed > 0:
            print("\nFailed tests:")
            for name, result in self.tests:
                if not result:
                    print(f"  ❌ {name}")
        
        return self.failed == 0


def test_basic_search():
    """Test basic search functionality"""
    # Use temporary database
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    config = UnifiedSearchConfig(db_path=db_path)
    client = UnifiedYouTubeSearch(config)
    
    # Initialize database
    database.initialize_database(db_path)
    
    # Add test data
    database.add_transcript(
        "test1", "Python Tutorial", "Tech Channel", "2024-01-01",
        "Learn Python programming basics", db_path=db_path
    )
    
    # Search
    results = client.search("Python", limit=10)
    
    # Cleanup
    import os
    os.unlink(db_path)
    
    return "results" in results and isinstance(results["results"], list)


def test_citation_detection():
    """Test citation detection"""
    detector = CitationDetector()
    text = "See arXiv:1706.03762 and doi:10.1038/nature123"
    
    citations = detector.detect_citations(text)
    
    # Should find at least 2 citations
    if len(citations) < 2:
        return False
    
    # Check citation types
    types = {c.type for c in citations}
    return "arxiv" in types and "doi" in types


def test_metadata_extraction():
    """Test metadata extraction"""
    extractor = MetadataExtractor()
    text = "Dr. Smith from MIT discusses machine learning"
    
    metadata = extractor.extract_all(text)
    
    # Should extract entities
    if "entities" not in metadata:
        return False
    
    # Should find person and organization
    labels = {e["label"] for e in metadata["entities"]}
    return "PERSON" in labels and "ORG" in labels


def test_search_widening():
    """Test search widening"""
    widener = SearchWidener()
    
    # Test synonym expansion
    result = widener.widen_search("ML", level=1)
    
    # Should widen the query
    return (
        result["query"] != "ML" and
        "widened" in result["explanation"].lower()
    )


def test_empty_search():
    """Test handling of empty results"""
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    config = UnifiedSearchConfig(db_path=db_path)
    client = UnifiedYouTubeSearch(config)
    database.initialize_database(db_path)
    
    # Search for non-existent content
    results = client.search("xyznonexistent123", limit=10)
    
    # Cleanup
    import os
    os.unlink(db_path)
    
    # Should return empty results gracefully
    return (
        "results" in results and
        len(results["results"]) == 0 and
        results.get("total_results", 0) == 0
    )


def test_multiple_citation_types():
    """Test detection of multiple citation types"""
    detector = CitationDetector()
    
    text = """
    Key papers:
    - Attention (Vaswani et al., 2017)
    - BERT at arXiv:1810.04805  
    - Nature review doi:10.1038/s41586-021-03819-2
    - Deep Learning book ISBN 978-0262035613
    """
    
    citations = detector.detect_citations(text)
    types = {c.type for c in citations}
    
    # Should detect multiple types
    expected_types = {"arxiv", "doi", "isbn", "paper", "author_year"}
    found_types = types.intersection(expected_types)
    
    return len(found_types) >= 3


def test_database_operations():
    """Test database save and search"""
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    database.initialize_database(db_path)
    
    # Save transcripts
    for i in range(3):
        database.add_transcript(
            f"vid{i}",
            f"Video {i}: Machine Learning",
            "ML Channel",
            "2024-01-01",
            f"Content about ML topic {i}",
            db_path=db_path
        )
    
    # Search
    results = database.search_transcripts("machine learning", limit=10, db_path=db_path)
    
    # Cleanup
    import os
    os.unlink(db_path)
    
    return (
        len(results) == 3 and  # Found all 3
        all("rank" in r for r in results)  # Has ranking
    )


def test_channel_filter():
    """Test channel filtering in search"""
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    database.initialize_database(db_path)
    
    # Add transcripts from different channels
    database.add_transcript("v1", "Video 1", "Channel A", "2024-01-01", "Content", db_path=db_path)
    database.add_transcript("v2", "Video 2", "Channel B", "2024-01-01", "Content", db_path=db_path)
    database.add_transcript("v3", "Video 3", "Channel A", "2024-01-01", "Content", db_path=db_path)
    
    # Search with filter
    results = database.search_transcripts("Content", channel_names=["Channel A"], db_path=db_path)
    
    # Cleanup
    import os
    os.unlink(db_path)
    
    # Should only return Channel A videos
    return (
        len(results) == 2 and
        all(r["channel_name"] == "Channel A" for r in results)
    )


def test_scientific_content():
    """Test scientific content analysis"""
    from youtube_transcripts.content_classifier import ContentClassifier
    
    classifier = ContentClassifier()
    
    lecture_text = "Welcome to lecture 5 of our graduate course on algorithms"
    tutorial_text = "Hey everyone! Quick tutorial on Python basics!"
    
    lecture_type = classifier.classify_content_type(lecture_text)
    tutorial_type = classifier.classify_content_type(tutorial_text)
    
    return (
        lecture_type == "lecture" and
        tutorial_type == "tutorial"
    )


def test_integration_ready():
    """Test that all components needed for integration are working"""
    try:
        # Import all required modules
        from youtube_transcripts.orchestrator_integration import YouTubeResearchModule
        from youtube_transcripts.search_enhancements import EnhancedSearch
        from youtube_transcripts.speaker_extractor import SpeakerExtractor
        
        # Create instances
        module = YouTubeResearchModule()
        enhanced = EnhancedSearch()
        speaker = SpeakerExtractor()
        
        # Basic functionality check
        return (
            hasattr(module, 'handle_message') and
            hasattr(enhanced, 'search') and
            hasattr(speaker, 'extract_speakers')
        )
    except Exception:
        return False


def main():
    """Run all level 0 tests"""
    print("YOUTUBE TRANSCRIPTS - LEVEL 0 INTERACTION TESTS")
    print("="*60)
    
    runner = Level0TestRunner()
    
    # Run tests
    runner.test("Basic search functionality", test_basic_search)
    runner.test("Citation detection", test_citation_detection)
    runner.test("Metadata extraction", test_metadata_extraction)
    runner.test("Search widening", test_search_widening)
    runner.test("Empty search handling", test_empty_search)
    runner.test("Multiple citation types", test_multiple_citation_types)
    runner.test("Database operations", test_database_operations)
    runner.test("Channel filtering", test_channel_filter)
    runner.test("Scientific content classification", test_scientific_content)
    runner.test("Integration components ready", test_integration_ready)
    
    # Summary
    success = runner.summary()
    
    if success:
        print("\n✅ All level 0 tests passed!")
        print("\nYouTube Transcripts is ready for:")
        print("  • Standalone operation")
        print("  • Integration with ArXiv MCP Server")
        print("  • Orchestration via claude-module-communicator")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())