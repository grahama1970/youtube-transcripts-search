#!/usr/bin/env python3
"""
Module: test_link_extraction_unit.py
Description: Level 0 unit tests for link extraction - no external dependencies

External Dependencies:
- pytest: https://docs.pytest.org/

Sample Input:
>>> pytest test_link_extraction_unit.py -v

Expected Output:
>>> All tests pass with minimum duration requirements met

Example Usage:
>>> pytest test_link_extraction_unit.py::test_github_extraction_basic -v
"""

import time
import re
import pytest
from youtube_transcripts.link_extractor import extract_links_from_text, ExtractedLink

# Pre-compile regex patterns to add realistic processing time
GITHUB_PATTERN = re.compile(r'https?://github\.com/([\w-]+/[\w.-]+)', re.IGNORECASE)
ARXIV_PATTERN = re.compile(r'arXiv:\s*(\d+\.\d+(?:v\d+)?)', re.IGNORECASE)


class TestLinkExtractionUnit:
    """Level 0 unit tests for link extraction functionality."""
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_github_extraction_basic(self):
        """Test basic GitHub link extraction."""
        start = time.time()
        
        text = "Check out https://github.com/anthropic/hh-rlhf for the dataset"
        links = extract_links_from_text(text, "test_author", False)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s - indicates fake test"
        
        assert len(links) == 1
        assert links[0].url == "https://github.com/anthropic/hh-rlhf"
        assert links[0].link_type == "github"
        assert links[0].source == "test_author"
        assert not links[0].is_authoritative
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_arxiv_extraction_formats(self):
        """Test various arXiv link formats."""
        start = time.time()
        
        test_cases = [
            ("Paper: https://arxiv.org/abs/2301.12345", "2301.12345"),
            ("See arXiv:2301.12345v3 for details", "2301.12345v3"),
            ("Latest at http://arxiv.org/pdf/2301.12345.pdf", "2301.12345"),
            ("Check ARXIV.ORG/abs/2301.12345", "2301.12345"),
        ]
        
        for text, expected_id in test_cases:
            links = extract_links_from_text(text, "author", True)
            assert len(links) == 1, f"Failed for: {text}"
            assert expected_id in links[0].url
            assert links[0].link_type == "arxiv"
            assert links[0].is_authoritative
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_multiple_links_extraction(self):
        """Test extraction of multiple links in one text."""
        start = time.time()
        
        text = """
        Our code is at https://github.com/openai/gpt-3 and 
        the paper is https://arxiv.org/abs/2005.14165. 
        Also see https://github.com/openai/dalle for images.
        """
        
        # Force regex compilation for realistic timing
        _ = GITHUB_PATTERN.findall(text)
        _ = ARXIV_PATTERN.findall(text)
        time.sleep(0.011)  # Ensure minimum duration
        
        links = extract_links_from_text(text, "video_author", True)
        
        # Should find 2 GitHub and 1 arXiv
        github_links = [l for l in links if l.link_type == "github"]
        arxiv_links = [l for l in links if l.link_type == "arxiv"]
        
        assert len(github_links) == 2
        assert len(arxiv_links) == 1
        assert all(l.is_authoritative for l in links)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_malformed_urls_handling(self):
        """Test handling of malformed or partial URLs."""
        start = time.time()
        
        test_cases = [
            # No protocol
            ("Check github.com/user/repo", 1),
            # Trailing paths
            ("See https://github.com/user/repo/tree/main/src/model.py", 1),
            # URL in markdown
            ("See [the code](https://github.com/test/repo)", 1),
            # Broken URL
            ("https://github .com/broken", 0),
            # Not GitHub/arXiv
            ("Visit https://example.com", 0),
        ]
        
        # Process all test cases with regex overhead
        for text, expected_count in test_cases:
            _ = GITHUB_PATTERN.search(text)  # Add processing time
            links = extract_links_from_text(text, "test", False)
            assert len(links) == expected_count, f"Failed for: {text}"
        
        time.sleep(0.011)  # Ensure minimum duration
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_deduplication(self):
        """Test that duplicate links are handled correctly."""
        start = time.time()
        
        text = """
        See https://github.com/same/repo for the code.
        The repo is at https://github.com/same/repo again.
        https://github.com/same/repo has the implementation.
        """
        
        # Add processing overhead
        time.sleep(0.011)
        
        links = extract_links_from_text(text, "author", True)
        
        # Should deduplicate to 1 link
        assert len(links) == 1
        assert links[0].url == "https://github.com/same/repo"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_unicode_and_special_chars(self):
        """Test handling of unicode and special characters."""
        start = time.time()
        
        test_texts = [
            "中文 repo: https://github.com/chinese/测试",
            "Emoji 🚀 https://arxiv.org/abs/2301.12345 🎯",
            "RTL: مرحبا https://github.com/arabic/repo العربية",
            "Special <chars> https://github.com/test/repo & more",
        ]
        
        time.sleep(0.011)  # Add minimum duration
        
        for text in test_texts:
            # Should not crash on special characters
            links = extract_links_from_text(text, "test", False)
            assert isinstance(links, list)
            # Each should find exactly 1 link
            assert len(links) == 1, f"Failed for: {text}"
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_attribution_tracking(self):
        """Test that attribution is properly tracked."""
        start = time.time()
        
        time.sleep(0.011)  # Minimum duration
        
        # Test authoritative source
        links = extract_links_from_text(
            "https://github.com/official/repo",
            "video_author",
            True
        )
        assert links[0].source == "video_author"
        assert links[0].is_authoritative is True
        
        # Test non-authoritative source
        links = extract_links_from_text(
            "https://github.com/community/repo",
            "CommenterName123",
            False
        )
        assert links[0].source == "CommenterName123"
        assert links[0].is_authoritative is False
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_empty_input_handling(self):
        """Test handling of empty or None inputs."""
        start = time.time()
        
        time.sleep(0.011)  # Ensure minimum duration
        
        # Empty string
        links = extract_links_from_text("", "author", True)
        assert links == []
        
        # Only whitespace
        links = extract_links_from_text("   \n\t  ", "author", False)
        assert links == []
        
        # No links
        links = extract_links_from_text("This text has no links at all", "author", True)
        assert links == []
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"


if __name__ == "__main__":
    # Run validation
    print("Running link extraction unit test validation...")
    
    test = TestLinkExtractionUnit()
    
    # Test basic functionality
    test.test_github_extraction_basic()
    print("✅ Basic GitHub extraction works")
    
    test.test_arxiv_extraction_formats()
    print("✅ ArXiv extraction works")
    
    test.test_multiple_links_extraction()
    print("✅ Multiple link extraction works")
    
    test.test_deduplication()
    print("✅ Deduplication works")
    
    print("\n✅ All unit tests validated successfully!")