"""
Module: config_20250605_180052.py
Description: Configuration management and settings

External Dependencies:
- None (uses only standard library)

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/config.py
import os
from pathlib import Path

# Environment variables or defaults
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
DB_PATH = Path("youtube_transcripts.db")
DEFAULT_CHANNEL = "https://www.youtube.com/@TrelisResearch"
DEFAULT_DATE_CUTOFF = "6 months"
DEFAULT_CLEANUP_MONTHS = 12
ADVANCED_INFERENCE_PATH = Path("./ADVANCED-inference")
