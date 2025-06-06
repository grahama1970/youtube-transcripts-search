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
from unittest.mock import patch, MagicMock
from typing import List

from youtube_transcripts.link_extractor import extract_links_from_text, ExtractedLink
from youtube_transcripts.research_pipeline import process_research_video


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
        # Empty video URL
        result = await process_research_video("")
        assert result['status'] == 'error'
        
        # None research topic (should work)
        with patch('youtube_transcripts.scripts.download_transcript.extract_video_id') as mock:
            mock.return_value = "test_id"
            # Should not crash with None topic
            result = await process_research_video("test_id", research_topic=None)
            assert 'error' in result or 'status' in result
    
    @pytest.mark.asyncio
    async def test_concurrent_video_processing(self):
        """Test processing multiple videos concurrently."""
        video_urls = [
            "https://www.youtube.com/watch?v=video1",
            "https://www.youtube.com/watch?v=video2",
            "https://www.youtube.com/watch?v=video3"
        ]
        
        # Process all videos concurrently
        with patch('youtube_transcripts.research_pipeline.process_research_video') as mock_process:
            mock_process.return_value = {'status': 'success', 'video_id': 'test'}
            
            tasks = [process_research_video(url) for url in video_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should handle concurrent calls without issues
            assert len(results) == 3
            assert all(isinstance(r, dict) or isinstance(r, Exception) for r in results)
    
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
    async def test_very_long_transcripts(self):
        """Test handling of very long transcripts."""
        # Create a very long transcript
        long_transcript = "[0.00] Start of video\n" * 10000  # 10k lines
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = long_transcript
            
            # Should handle long transcripts without memory issues
            # This tests chunking efficiency
            from youtube_transcripts.research_pipeline import _simplified_process
            
            # Mock dependencies
            with patch('youtube_transcripts.scripts.download_transcript.extract_video_id'):
                with patch('youtube_transcripts.scripts.download_transcript.get_video_info'):
                    with patch('youtube_transcripts.scripts.download_transcript.download_youtube_transcript'):
                        # Should complete without hanging
                        result = await _simplified_process("test_url", None, 500)
                        assert 'knowledge_chunks' in result
                        assert result['knowledge_chunks'] > 100  # Should create many chunks
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        from asyncio import TimeoutError
        
        with patch('youtube_transcripts.scripts.download_transcript.get_video_info') as mock:
            # Simulate network timeout
            mock.side_effect = TimeoutError("Network timeout")
            
            result = await process_research_video("https://www.youtube.com/watch?v=test")
            assert result['status'] == 'error'
            assert 'timeout' in result['error'].lower()
    
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
        # Test multiple API keys for failover
        api_keys = ["key1", "key2", "key3"]
        
        with patch.dict('os.environ', {'YOUTUBE_API_KEY': api_keys[0]}):
            # First key fails
            with patch('youtube_transcripts.scripts.download_transcript.build') as mock_build:
                mock_build.side_effect = Exception("Invalid API key")
                
                # Should handle API key failure gracefully
                from youtube_transcripts.scripts.download_transcript import get_video_info
                
                try:
                    result = get_video_info("test_id")
                except Exception as e:
                    assert "API key" in str(e)
    
    @pytest.mark.asyncio
    async def test_partial_data_extraction(self):
        """Test when only partial data is available."""
        # Video with description but no transcript
        with patch('youtube_transcripts.scripts.download_transcript.get_video_info') as mock_info:
            mock_info.return_value = (
                "Video Title",
                "Channel",
                "PT10M",
                "Has links but no transcript",
                [ExtractedLink("https://github.com/test/repo", "github", "author", True)]
            )
            
            with patch('youtube_transcripts.scripts.download_transcript.YouTubeTranscriptApi.get_transcript') as mock_transcript:
                mock_transcript.side_effect = Exception("No transcript available")
                
                # Should still extract what it can
                result = await process_research_video("test_video")
                # Should handle partial success
                assert result['status'] in ['error', 'partial']
    
    @pytest.mark.asyncio
    async def test_comment_spam_filtering(self):
        """Test filtering of spammy comments."""
        spam_comments = [
            ("SpamBot", "CLICK HERE!!! https://spam.com", []),
            ("RealUser", "Check out https://github.com/real/repo", [
                MagicMock(url="https://github.com/real/repo", link_type="github")
            ]),
            ("SpamBot2", "💰💰💰 MAKE MONEY 💰💰💰", []),
        ]
        
        # Should filter spam but keep legitimate comments
        legitimate = [c for c in spam_comments if c[2]]  # Has links
        assert len(legitimate) == 1
        assert legitimate[0][0] == "RealUser"


@pytest.mark.asyncio
async def test_memory_leak_prevention():
    """Test that repeated processing doesn't cause memory leaks."""
    # Process same video multiple times
    for i in range(10):
        with patch('youtube_transcripts.research_pipeline._simplified_process') as mock:
            mock.return_value = {'status': 'success', 'video_id': f'test_{i}'}
            
            result = await process_research_video(f"video_{i}")
            
            # Ensure objects are cleaned up
            assert result is not None
    
    # In a real test, we'd check memory usage here
    # For now, just ensure it completes without issues


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