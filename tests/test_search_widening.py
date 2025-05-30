#!/usr/bin/env python3
"""
Test search widening functionality
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from youtube_transcripts.core.database import initialize_database, add_transcript
from youtube_transcripts.search_widener import SearchWidener, SearchWidenerResult


class TestSearchWidening:
    """Test progressive search widening"""
    
    @pytest.fixture
    def test_db(self):
        """Create test database with specific data"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        # Initialize database
        initialize_database(db_path)
        
        # Add test data with specific terms
        test_transcripts = [
            {
                "video_id": "volcano_engine_001",
                "title": "Volcano Engine Tutorial",
                "channel_name": "TechChannel",
                "publish_date": "2025-05-20",
                "transcript": "Learn about Volcano Engine and its reinforcement learning capabilities.",
                "summary": "Volcano Engine overview"
            },
            {
                "video_id": "rl_guide_001",
                "title": "Reinforcement Learning Guide",
                "channel_name": "AIChannel",
                "publish_date": "2025-05-19",
                "transcript": "A comprehensive guide to reinforcement learning techniques.",
                "summary": "RL guide"
            },
            {
                "video_id": "ml_tutorial_001",
                "title": "Machine Learning Tutorial",
                "channel_name": "MLChannel",
                "publish_date": "2025-05-18",
                "transcript": "Introduction to machine learning concepts and algorithms.",
                "summary": "ML basics"
            }
        ]
        
        for transcript in test_transcripts:
            add_transcript(**transcript, db_path=db_path)
        
        yield db_path
        db_path.unlink(missing_ok=True)
    
    def test_exact_match_no_widening(self, test_db):
        """Test that exact matches don't trigger widening"""
        widener = SearchWidener(db_path=test_db)
        
        result = widener.search_with_widening("Volcano Engine")
        
        assert result.widening_level == 0
        assert result.widening_technique == "exact match"
        assert len(result.results) > 0
        assert "volcano_engine_001" in [r['video_id'] for r in result.results]
    
    def test_synonym_expansion(self, test_db):
        """Test synonym expansion for known terms"""
        widener = SearchWidener(db_path=test_db)
        
        # Search for VERL which should expand to include Volcano Engine
        result = widener.search_with_widening("VERL", max_widening_level=4)
        
        assert result.widening_level > 0
        # The technique could be synonym expansion or semantic expansion
        assert any(technique in result.widening_technique.lower() 
                  for technique in ["synonym", "semantic", "stem", "fuzzy"])
        assert len(result.results) > 0
        # Verify we found Volcano Engine content
        assert any("volcano" in r['transcript'].lower() for r in result.results)
    
    def test_fuzzy_matching(self, test_db):
        """Test fuzzy matching for partial terms"""
        widener = SearchWidener(db_path=test_db)
        
        # Search for partial term
        result = widener.search_with_widening("reinforce")
        
        # Should find reinforcement learning content
        assert len(result.results) > 0
        assert any("reinforcement" in r['transcript'].lower() for r in result.results)
    
    def test_no_results_after_widening(self, test_db):
        """Test when no results found even after widening"""
        widener = SearchWidener(db_path=test_db)
        
        result = widener.search_with_widening("quantum computing blockchain")
        
        assert result.widening_level > 0
        assert len(result.results) == 0
        assert "No results found" in result.explanation
    
    def test_widening_with_channels(self, test_db):
        """Test widening with channel filtering"""
        widener = SearchWidener(db_path=test_db)
        
        # Search in specific channel
        result = widener.search_with_widening(
            "VERL",
            channel_names=["TechChannel"]
        )
        
        if result.results:
            assert all(r['channel_name'] == "TechChannel" for r in result.results)
    
    def test_semantic_expansion(self, test_db):
        """Test semantic expansion for related concepts"""
        widener = SearchWidener(db_path=test_db)
        
        # Add more test data with semantically related terms
        add_transcript(
            video_id="tutorial_001",
            title="Complete Guide to ML",
            channel_name="TutorialChannel",
            publish_date="2025-05-17",
            transcript="This guide covers machine learning from basics to advanced.",
            db_path=test_db
        )
        
        # Search for "tutorial" should find "guide" as well
        result = widener.search_with_widening("nonexistent tutorial xyz")
        
        assert result.widening_level > 0
        assert len(result.results) > 0
        assert any("guide" in r['title'].lower() for r in result.results)
    
    def test_widening_explanation(self, test_db):
        """Test that explanations are user-friendly"""
        widener = SearchWidener(db_path=test_db)
        
        result = widener.search_with_widening("VERL")
        
        assert result.explanation
        assert result.original_query in result.explanation
        assert str(len(result.results)) in result.explanation
        assert "level:" in result.explanation.lower() or "widening" in result.explanation.lower()


def generate_widening_test_report():
    """Generate test report for search widening"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(__file__).parent.parent / "docs" / "reports" / f"search_widening_report_{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write("# Search Widening Test Report\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n")
        f.write("**Component**: Progressive Search Widening\n\n")
        
        f.write("## Features Tested\n\n")
        f.write("- Exact match (no widening needed)\n")
        f.write("- Synonym expansion (VERL → Volcano Engine)\n")
        f.write("- Word stemming\n")
        f.write("- Fuzzy matching\n")
        f.write("- Semantic expansion\n")
        f.write("- Channel filtering with widening\n")
        f.write("- User-friendly explanations\n")
        
        f.write("\n## Widening Techniques\n\n")
        f.write("1. **Level 1**: Synonym expansion - adds known synonyms and related terms\n")
        f.write("2. **Level 2**: Word stemming - removes suffixes to find root words\n")
        f.write("3. **Level 3**: Fuzzy matching - uses wildcards for partial matches\n")
        f.write("4. **Level 4**: Semantic expansion - includes conceptually related terms\n")
    
    return report_path


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])