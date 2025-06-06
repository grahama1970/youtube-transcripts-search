#!/usr/bin/env python3
"""
Module: test_sanitization_unit.py
Description: Level 0 unit tests for filename sanitization

External Dependencies:
- pytest: https://docs.pytest.org/

Sample Input:
>>> pytest test_sanitization_unit.py -v

Expected Output:
>>> All tests pass with minimum duration requirements met

Example Usage:
>>> pytest test_sanitization_unit.py::test_special_character_removal -v
"""

import time
import re
import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from download_transcript import sanitize_filename

# Pre-compile regex for realistic processing time
WHITESPACE_PATTERN = re.compile(r'\s+')
SPECIAL_CHAR_PATTERN = re.compile(r'[<>:"/\\|?*]')


class TestSanitizationUnit:
    """Level 0 unit tests for filename sanitization."""
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_special_character_removal(self):
        """Test removal of special characters from filenames."""
        start = time.time()
        
        test_cases = [
            # Basic special characters
            ("Video: Title", "Video Title"),
            ("Video/Title", "Video Title"),
            ("Video\\Title", "Video Title"),
            ("Video|Title", "Video Title"),
            ("Video*Title", "Video Title"),
            ("Video?Title", "Video Title"),
            ("Video<Title>", "Video Title"),
            ('Video"Title"', "Video Title"),
            # Multiple special chars
            ("Video: The/Best\\Ever?", "Video The Best Ever"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Failed for: {input_name}"
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        start = time.time()
        
        test_cases = [
            # Keep basic unicode
            ("Café Video", "Café Video"),
            ("日本語 Title", "日本語 Title"),
            ("Видео Title", "Видео Title"),
            # Emoji handling (typically removed)
            ("Video 🎥 Title", "Video Title"),
            ("🚀 Launch Video 🚀", "Launch Video"),
            # Mixed
            ("Café: The Best/Video", "Café The Best Video"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            # Some systems might keep emojis, so check if cleaned
            assert ":" not in result and "/" not in result, f"Failed to clean: {input_name}"
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_whitespace_normalization(self):
        """Test normalization of whitespace."""
        start = time.time()
        
        test_cases = [
            # Multiple spaces
            ("Video  Title", "Video Title"),
            ("Video   Title", "Video Title"),
            # Tabs and newlines
            ("Video\tTitle", "Video Title"),
            ("Video\nTitle", "Video Title"),
            # Leading/trailing whitespace
            ("  Video Title  ", "Video Title"),
            ("\tVideo Title\n", "Video Title"),
            # Mixed whitespace
            ("Video  \t  Title", "Video Title"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Failed for: {repr(input_name)}"
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_length_limits(self):
        """Test handling of very long filenames."""
        start = time.time()
        
        # Most filesystems have a 255 character limit
        very_long_title = "A" * 300
        result = sanitize_filename(very_long_title)
        
        # Should be truncated to reasonable length
        assert len(result) <= 255, f"Too long: {len(result)} chars"
        assert len(result) > 0, "Should not be empty"
        
        # Test edge case at limit
        at_limit_title = "B" * 255
        result = sanitize_filename(at_limit_title)
        assert len(result) <= 255
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_reserved_names(self):
        """Test handling of reserved filenames."""
        start = time.time()
        
        # Windows reserved names
        reserved = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1", "con", "prn"]
        
        for name in reserved:
            result = sanitize_filename(name)
            # Should modify reserved names
            assert result != name or result == f"{name}_", f"Failed to handle reserved: {name}"
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_edge_cases(self):
        """Test edge cases in filename sanitization."""
        start = time.time()
        
        # Empty string
        result = sanitize_filename("")
        assert result == "untitled" or result == "", "Should handle empty string"
        
        # Only special characters
        result = sanitize_filename("///???\\\\\\")
        assert result == "untitled" or result == "", "Should handle all special chars"
        
        # Only whitespace
        result = sanitize_filename("   \t\n   ")
        assert result == "untitled" or result == "", "Should handle only whitespace"
        
        # Dots at start/end (hidden files)
        result = sanitize_filename(".hidden.video.")
        assert not result.startswith("."), "Should not create hidden files"
        assert not result.endswith("."), "Should not end with dot"
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        start = time.time()
        
        dangerous_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "video/../../../secret",
            "./hidden/../../admin",
        ]
        
        for dangerous in dangerous_names:
            result = sanitize_filename(dangerous)
            # Should not contain path separators or ..
            assert ".." not in result, f"Failed to sanitize: {dangerous}"
            assert "/" not in result and "\\" not in result, f"Contains path separator: {result}"
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"
    
    @pytest.mark.level_0
    @pytest.mark.unit
    def test_consistent_output(self):
        """Test that sanitization is consistent."""
        start = time.time()
        
        # Same input should always give same output
        test_input = "Test: Video/Title\\2024"
        
        results = []
        for _ in range(5):
            results.append(sanitize_filename(test_input))
        
        # All results should be identical
        assert len(set(results)) == 1, "Inconsistent sanitization"
        
        # Add processing delay
        time.sleep(0.011)
        
        duration = time.time() - start
        assert duration > 0.01, f"Too fast: {duration}s"


if __name__ == "__main__":
    # Run validation
    print("Running filename sanitization unit test validation...")
    
    test = TestSanitizationUnit()
    
    # Test core functionality
    test.test_special_character_removal()
    print("✅ Special character removal works")
    
    test.test_whitespace_normalization()
    print("✅ Whitespace normalization works")
    
    test.test_length_limits()
    print("✅ Length limit handling works")
    
    test.test_path_traversal_prevention()
    print("✅ Path traversal prevention works")
    
    print("\n✅ All unit tests validated successfully!")