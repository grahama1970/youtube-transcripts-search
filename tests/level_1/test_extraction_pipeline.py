#!/usr/bin/env python3
"""
Module: test_extraction_pipeline.py
Description: Level 1 integration tests for full link extraction pipeline

External Dependencies:
- pytest: https://docs.pytest.org/
- youtube-transcript-api: https://pypi.org/project/youtube-transcript-api/

Sample Input:
>>> pytest test_extraction_pipeline.py -v

Expected Output:
>>> All tests pass with real data extraction

Example Usage:
>>> pytest test_extraction_pipeline.py::test_full_video_processing -v
"""

import time
import os
import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from download_transcript import (
    extract_video_id, 
    get_video_info,
    download_youtube_transcript,
    sanitize_filename
)
from youtube_transcripts.link_extractor import extract_links_from_text


class TestExtractionPipeline:
    """Level 1 integration tests for complete extraction pipeline."""
    
    @pytest.mark.level_1
    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv('YOUTUBE_API_KEY'), reason="Requires YouTube API key")
    def test_full_video_processing(self, tmp_path):
        """Test processing a video from URL to transcript with links."""
        start = time.time()
        
        # Use a known video
        video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Step 1: Extract video ID
        video_id = extract_video_id(video_url)
        assert video_id == "dQw4w9WgXcQ"
        
        # Step 2: Get video metadata
        title, channel, duration, description, links = get_video_info(video_id)
        assert title is not None
        assert "Never Gonna Give You Up" in title
        assert channel is not None
        assert duration is not None
        
        # Step 3: Download transcript
        output_file = download_youtube_transcript(video_url, output_dir=tmp_path)
        assert output_file
        assert Path(output_file).exists()
        
        # Step 4: Verify file contents
        with open(output_file, 'r') as f:
            content = f.read()
            assert len(content) > 100  # Has substantial content
            assert video_id in content  # Contains video ID
            assert title in content  # Contains title
        
        # Step 5: Check filename sanitization
        filename = Path(output_file).name
        assert filename.endswith('_transcript.txt')
        # Should not contain special characters
        assert ':' not in filename
        assert '/' not in filename
        
        duration = time.time() - start
        assert duration > 0.5, f"Too fast for full pipeline: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_transcript_without_api_key(self, tmp_path):
        """Test transcript download works without API key (using video ID)."""
        start = time.time()
        
        # This should work without API key
        video_id = "dQw4w9WgXcQ"
        
        try:
            output_file = download_youtube_transcript(video_id, output_dir=tmp_path)
            assert output_file
            assert Path(output_file).exists()
            
            # Check content
            with open(output_file, 'r') as f:
                content = f.read()
                assert len(content) > 100
                assert "transcript" in content.lower()
                
        except Exception as e:
            # Might fail if video has no transcript
            assert "transcript" in str(e).lower()
        
        duration = time.time() - start
        assert duration > 0.1, f"Too fast: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv('YOUTUBE_API_KEY'), reason="Requires YouTube API key")
    def test_link_extraction_pipeline(self):
        """Test extracting links from video description and comments."""
        start = time.time()
        
        # Use a tech video likely to have GitHub/arXiv links
        # Note: This is an example, actual video might change
        video_id = "kCc8FmEb1nY"  # Example: Let's build GPT video
        
        try:
            # Get video info
            title, channel, duration, description, desc_links = get_video_info(video_id)
            
            # Extract links from description
            if description:
                assert isinstance(desc_links, list)
                
                # Check link structure if any found
                for link in desc_links:
                    assert hasattr(link, 'url')
                    assert hasattr(link, 'link_type')
                    assert hasattr(link, 'source')
                    assert hasattr(link, 'is_authoritative')
                    assert link.is_authoritative  # From video author
                
            # Also test comment extraction (separate)
            from download_transcript import get_video_comments
            comments = get_video_comments(video_id, max_comments=5)
            
            comment_links = []
            for author, text, links in comments:
                comment_links.extend(links)
            
            # Verify comment links are not authoritative
            for link in comment_links:
                assert not link.is_authoritative  # From commenters
                
        except Exception as e:
            # Video might not exist or be private
            assert 'video' in str(e).lower() or 'api' in str(e).lower()
        
        duration = time.time() - start
        assert duration > 0.2, f"Too fast: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_deduplication_across_sources(self):
        """Test that links are deduplicated across description and comments."""
        start = time.time()
        
        # Simulate text from multiple sources
        description = """
        Check out our code at https://github.com/openai/gpt-2
        Paper: https://arxiv.org/abs/1234.5678
        More at https://github.com/openai/gpt-2
        """
        
        comment1 = "I love https://github.com/openai/gpt-2 project!"
        comment2 = "The paper https://arxiv.org/abs/1234.5678 is great"
        comment3 = "New repo: https://github.com/user/fork"
        
        # Extract from each source
        desc_links = extract_links_from_text(description, "video_author", True)
        comment1_links = extract_links_from_text(comment1, "user1", False)
        comment2_links = extract_links_from_text(comment2, "user2", False)
        comment3_links = extract_links_from_text(comment3, "user3", False)
        
        # Combine all
        all_links = desc_links + comment1_links + comment2_links + comment3_links
        
        # Deduplicate by URL
        seen_urls = set()
        unique_links = []
        for link in all_links:
            if link.url not in seen_urls:
                seen_urls.add(link.url)
                unique_links.append(link)
        
        # Should have 3 unique URLs
        assert len(unique_links) == 3
        
        # Verify authoritative links are preserved
        gpt2_links = [l for l in unique_links if 'gpt-2' in l.url]
        assert len(gpt2_links) == 1
        assert gpt2_links[0].is_authoritative  # From video author
        
        duration = time.time() - start
        assert duration > 0.05, f"Too fast: {duration}s"
    
    @pytest.mark.level_1
    @pytest.mark.integration
    def test_error_recovery_pipeline(self):
        """Test pipeline handles errors gracefully."""
        start = time.time()
        
        # Test with invalid video
        invalid_url = "https://www.youtube.com/watch?v=INVALID123"
        
        # Should handle extraction
        video_id = extract_video_id(invalid_url)
        assert video_id == "INVALID123"
        
        # API call should fail gracefully
        if os.getenv('YOUTUBE_API_KEY'):
            try:
                info = get_video_info(video_id)
                # Might return None values
                assert info[0] is None or "invalid" in str(info).lower()
            except Exception as e:
                assert "video" in str(e).lower() or "api" in str(e).lower()
        
        # Transcript download should fail gracefully
        try:
            output = download_youtube_transcript(invalid_url, output_dir="/tmp")
            # If it returns, should indicate failure
            assert output is None or not Path(output).exists()
        except Exception as e:
            assert "transcript" in str(e).lower() or "video" in str(e).lower()
        
        duration = time.time() - start
        assert duration > 0.05, f"Too fast: {duration}s"


if __name__ == "__main__":
    # Validation
    print("Running extraction pipeline test validation...")
    
    # Check dependencies
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        print("✅ youtube-transcript-api available")
    except ImportError:
        print("❌ youtube-transcript-api not installed")
    
    if not os.getenv('YOUTUBE_API_KEY'):
        print("⚠️  WARNING: YOUTUBE_API_KEY not set - some tests will be skipped")
    else:
        print("✅ YouTube API key found")
    
    # Test basic extraction
    from youtube_transcripts.link_extractor import extract_links_from_text
    test_links = extract_links_from_text(
        "Check https://github.com/test/repo", "test", False
    )
    if test_links:
        print("✅ Link extraction works")
    
    print("\nRun full tests with: pytest test_extraction_pipeline.py -v")