#!/usr/bin/env python3
"""
Module: test_video_id_unit.py
Description: Level 0 unit tests for YouTube video ID extraction

External Dependencies:
- pytest: https://docs.pytest.org/

Sample Input:
>>> pytest test_video_id_unit.py -v

Expected Output:
>>> All tests pass with minimum duration requirements met

Example Usage:
>>> pytest test_video_id_unit.py::test_standard_url_formats -v
"""

import time
import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from download_transcript import extract_video_id


class TestVideoIdUnit:
    """Level 0 unit tests for video ID extraction."""
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_standard_url_formats(self):
        """Test extraction from standard YouTube URL formats."""
        start = time.time()
        
        test_cases = [
            # Standard watch URL
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # With additional parameters
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
            # Mobile URL
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # Without www
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # With playlist
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_cases:
            video_id = extract_video_id(url)
            assert video_id == expected_id, f"Failed for URL: {url}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_short_url_formats(self):
        """Test extraction from shortened YouTube URLs."""
        start = time.time()
        
        test_cases = [
            # youtu.be format
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # With timestamp
            ("https://youtu.be/dQw4w9WgXcQ?t=42", "dQw4w9WgXcQ"),
            # Without https
            ("youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_cases:
            video_id = extract_video_id(url)
            assert video_id == expected_id, f"Failed for URL: {url}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_embed_url_formats(self):
        """Test extraction from embed URLs."""
        start = time.time()
        
        test_cases = [
            # Standard embed
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # With parameters
            ("https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1", "dQw4w9WgXcQ"),
            # Nocookie domain
            ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_cases:
            video_id = extract_video_id(url)
            assert video_id == expected_id, f"Failed for URL: {url}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_direct_video_id(self):
        """Test when given a direct video ID instead of URL."""
        start = time.time()
        
        # Should return the ID as-is
        video_ids = ["dQw4w9WgXcQ", "9bZkp7q19f0", "_-abcDEF123"]
        
        for video_id in video_ids:
            result = extract_video_id(video_id)
            assert result == video_id, f"Failed for ID: {video_id}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_invalid_urls(self):
        """Test handling of invalid URLs."""
        start = time.time()
        
        invalid_cases = [
            "",  # Empty string
            "not a url",  # Random text
            "https://vimeo.com/123456",  # Wrong site
            "https://www.youtube.com/",  # No video
            "https://www.youtube.com/channel/UC123",  # Channel URL
            "https://www.youtube.com/playlist?list=PL123",  # Playlist URL
        ]
        
        for invalid_url in invalid_cases:
            result = extract_video_id(invalid_url)
            # Should return the input or None for invalid URLs
            assert result == invalid_url or result is None, f"Unexpected result for: {invalid_url}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_edge_cases(self):
        """Test edge cases in video ID extraction."""
        start = time.time()
        
        edge_cases = [
            # Multiple v parameters (should take first)
            ("https://www.youtube.com/watch?v=first&v=second", "first"),
            # Special characters in ID
            ("https://www.youtube.com/watch?v=_-abcDEF123", "_-abcDEF123"),
            # Very long ID (YouTube IDs are 11 chars)
            ("https://www.youtube.com/watch?v=12345678901", "12345678901"),
            # URL with fragment
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ#t=30s", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in edge_cases:
            video_id = extract_video_id(url)
            assert video_id == expected_id, f"Failed for URL: {url}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_case_sensitivity(self):
        """Test that extraction handles case variations."""
        start = time.time()
        
        # YouTube video IDs are case-sensitive
        test_cases = [
            ("https://www.YOUTUBE.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("HTTPS://WWW.YOUTUBE.COM/WATCH?V=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?V=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_cases:
            video_id = extract_video_id(url)
            assert video_id == expected_id, f"Failed for URL: {url}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"


if __name__ == "__main__":
    # Run validation
    print("Running video ID extraction unit test validation...")
    
    test = TestVideoIdUnit()
    
    # Test core functionality
    test.test_standard_url_formats()
    print("✅ Standard URL extraction works")
    
    test.test_short_url_formats()
    print("✅ Short URL extraction works")
    
    test.test_direct_video_id()
    print("✅ Direct ID handling works")
    
    test.test_invalid_urls()
    print("✅ Invalid URL handling works")
    
    print("\n✅ All unit tests validated successfully!")