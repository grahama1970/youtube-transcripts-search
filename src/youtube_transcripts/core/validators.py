"""
Module: validators.py
Description: Functions for validators operations

External Dependencies:
- None (uses only standard library)

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/core/validators.py
import re
from datetime import datetime


def validate_youtube_url(url: str) -> bool:
    """Validate YouTube channel or video URL"""
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/@[\w-]+/?$',  # New channel format
        r'^https?://(?:www\.)?youtube\.com/c/[\w-]+/?$',  # /c/ format
        r'^https?://(?:www\.)?youtube\.com/channel/[\w-]+/?$',  # /channel/ format
        r'^https?://(?:www\.)?youtube\.com/user/[\w-]+/?$',  # /user/ format
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}',  # Video URL
        r'^https?://youtu\.be/[\w-]{11}'  # Short video URL
    ]

    return any(re.match(pattern, url) for pattern in patterns)

def validate_date_cutoff(date_str: str) -> str | None:
    """Validate date cutoff string"""
    # Check for relative date (e.g., "6 months")
    relative_pattern = r'^(\d+)\s*months?$'
    match = re.match(relative_pattern, date_str.lower())
    if match:
        return date_str

    # Check for absolute date (YYYY-MM-DD)
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Limit length
    if len(filename) > 200:
        filename = filename[:200]

    return filename.strip()
