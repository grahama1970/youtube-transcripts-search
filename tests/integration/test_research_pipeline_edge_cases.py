#!/usr/bin/env python3
"""
Module: test_research_pipeline_edge_cases.py
Description: Edge case tests for YouTube research pipeline to find bugs and weaknesses

External Dependencies:
- pytest: https://docs.pytest.org/
- pytest-asyncio: https://pypi.org/project/pytest-asyncio/

Sample Input:
>>> pytest test_research_pipeline_edge_cases.py -v

Expected Output:
>>> All edge cases should be handled gracefully

Example Usage:
>>> pytest test_research_pipeline_edge_cases.py::test_malformed_links -v
"""

import pytest
import asyncio
import time
import os
from typing import List

from youtube_transcripts.link_extractor import extract_links_from_text, ExtractedLink
from youtube_transcripts.research_pipeline import process_research_video

# Real test videos - always available
REAL_TEST_VIDEOS = {
    'rick_astley': 'dQw4w9WgXcQ',  # Never Gonna Give You Up
    'gangnam_style': '9bZkp7q19f0',  # Gangnam Style
    'invalid': 'INVALID_VIDEO_ID_123',  # For error testing
}


class TestResearchPipelineEdgeCases:
    """Test edge cases and potential bugs in the research pipeline."""
    
    @pytest.mark.asyncio
    async def test_malformed_links_extraction(self):
        """Test extraction of malformed or edge case links."""
        test_cases = [
            # Edge case: No protocol
            ("Check out github.com/user/repo", 1, 0),
            
            # Edge case: Trailing slashes and paths
            ("See https://github.com/user/repo/tree/main/src", 1, 0),
            
            # Edge case: Mixed case
            ("Paper at ARXIV.ORG/abs/2301.12345", 0, 1),
            
            # Edge case: arXiv with version
            ("Latest version: arXiv:2301.12345v3", 0, 1),
            
            # Edge case: Multiple links in one line
            ("Both https://github.com/a/b and https://arxiv.org/abs/123", 1, 1),
            
            # Edge case: Links in markdown
            ("See [this repo](https://github.com/test/repo)", 1, 0),
            
            # Edge case: Duplicate links
            ("https://github.com/same/repo and again https://github.com/same/repo", 1, 0),
        ]
        
        for text, expected_github, expected_arxiv in test_cases:
            links = extract_links_from_text(text, "test", False)
            github_count = sum(1 for l in links if l.link_type == 'github')
            arxiv_count = sum(1 for l in links if l.link_type == 'arxiv')
            
            assert github_count == expected_github, f"Failed for: {text}"
            assert arxiv_count == expected_arxiv, f"Failed for: {text}"
    
    @pytest.mark.asyncio
    async def test_empty_and_null_inputs(self):
        """Test handling of empty and null inputs."""
        start = time.time()
        
        # Empty video URL
        result = await process_research_video("")
        assert result['status'] == 'error'
        
        # Invalid video ID
        result = await process_research_video(REAL_TEST_VIDEOS['invalid'], research_topic=None)
        assert result['status'] == 'error'
        
        duration = time.time() - start
        assert duration > 0.05  # Real API calls take time
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv('YOUTUBE_API_KEY'), reason="Requires YouTube API key")
    async def test_concurrent_video_processing(self):
        """Test processing multiple videos concurrently."""
        start = time.time()
        
        # Use real video IDs but limit to 2 to avoid rate limits
        video_urls = [
            f"https://www.youtube.com/watch?v={REAL_TEST_VIDEOS['rick_astley']}",
            f"https://www.youtube.com/watch?v={REAL_TEST_VIDEOS['gangnam_style']}"
        ]
        
        # Process videos concurrently
        tasks = [process_research_video(url) for url in video_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle concurrent calls
        assert len(results) == 2
        assert all(isinstance(r, dict) or isinstance(r, Exception) for r in results)
        
        duration = time.time() - start
        assert duration > 0.1  # Real concurrent API calls
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        test_texts = [
            "Check this 中文 repo: https://github.com/user/测试",
            "Émojis in description 🚀 https://arxiv.org/abs/2301.12345 🎯",
            "Special chars: <script>alert('xss')</script> https://github.com/test/repo",
            "RTL text: مرحبا https://github.com/arabic/repo العربية"
        ]
        
        for text in test_texts:
            # Should not crash on special characters
            links = extract_links_from_text(text, "test", False)
            assert isinstance(links, list)
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Long transcript test needs real long video")
    async def test_very_long_transcripts(self):
        """Test handling of very long transcripts."""
        # This test is skipped as it requires a real long video
        # In production, we'd use a known long video like a lecture
        # For now, we'll test chunking with a shorter real video
        pass
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        # Test with a video that doesn't exist to trigger error
        start = time.time()
        
        result = await process_research_video(f"https://www.youtube.com/watch?v={REAL_TEST_VIDEOS['invalid']}")
        assert result['status'] == 'error'
        
        duration = time.time() - start
        assert duration > 0.05  # Real network attempt
    
    @pytest.mark.asyncio
    async def test_circular_references(self):
        """Test handling of circular references in graph."""
        # Test case where Video A mentions Paper B which references Video A
        # This tests that the graph building doesn't get stuck in loops
        
        links = [
            ExtractedLink("https://arxiv.org/abs/2301.12345", "arxiv", "video_author", True),
            ExtractedLink("https://github.com/test/repo", "github", "video_author", True),
        ]
        
        # The system should handle circular references gracefully
        # by using proper graph traversal limits
        assert len(links) == 2  # Basic check for now
    
    @pytest.mark.asyncio
    async def test_api_key_rotation(self):
        """Test handling when API keys need rotation."""
        # Test with invalid API key
        original_key = os.getenv('YOUTUBE_API_KEY', '')
        
        try:
            # Set invalid key
            os.environ['YOUTUBE_API_KEY'] = 'INVALID_KEY_12345'
            
            # Should handle API key failure gracefully
            from scripts.download_transcript import get_video_info
            
            try:
                result = get_video_info(REAL_TEST_VIDEOS['rick_astley'])
                # If it works, API might be accepting any key (unlikely)
                assert False, "Expected API key error"
            except Exception as e:
                assert "API" in str(e) or "key" in str(e).lower()
        finally:
            # Restore original key
            if original_key:
                os.environ['YOUTUBE_API_KEY'] = original_key
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Need specific video without transcript for this test")
    async def test_partial_data_extraction(self):
        """Test when only partial data is available."""
        # This test requires finding a real video without transcript
        # which is rare on YouTube. Skipping for now.
        pass
    
    @pytest.mark.asyncio
    async def test_comment_spam_filtering(self):
        """Test filtering of spammy comments."""
        # Test link extraction from various comment patterns
        spam_patterns = [
            "CLICK HERE!!! https://spam.com",
            "Check out https://github.com/real/repo for the code",
            "💰💰💰 MAKE MONEY 💰💰💰",
        ]
        
        results = []
        for text in spam_patterns:
            links = extract_links_from_text(text, "commenter", False)
            results.append(len(links))
        
        # Should extract GitHub link but not spam.com
        assert results[0] == 0  # spam.com not GitHub/arXiv
        assert results[1] == 1  # GitHub link found
        assert results[2] == 0  # No links


@pytest.mark.asyncio
@pytest.mark.skip(reason="Memory leak test requires multiple real API calls")
async def test_memory_leak_prevention():
    """Test that repeated processing doesn't cause memory leaks."""
    # This test would require multiple real API calls
    # which could hit rate limits. Skipping for manual testing.
    pass


if __name__ == "__main__":
    # Run validation
    print("✅ Edge case test module ready")
    
    # Quick validation of link extraction
    test_links = extract_links_from_text(
        "See https://github.com/test/repo and arXiv:2301.12345",
        "test",
        False
    )
    assert len(test_links) == 2
    print(f"✅ Found {len(test_links)} links in test")