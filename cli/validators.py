# youtube_transcripts/cli/validators.py
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urlparse
import re

def validate_channel_urls(channels: str) -> List[str]:
    """Validate comma-separated YouTube channel URLs."""
    urls = [url.strip() for url in channels.split(',')]
    for url in urls:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc or not re.match(r'^https?://(www\.)?youtube\.com/(@[a-zA-Z0-9_-]+|channel/[a-zA-Z0-9_-]+)$', url):
            raise ValueError(f"Invalid YouTube channel URL: {url}")
    return urls

def validate_date_cutoff(cutoff: str) -> str:
    """Validate date cutoff format."""
    if 'month' in cutoff.lower():
        try:
            months = int(cutoff.split()[0])
            if months <= 0:
                raise ValueError
        except (ValueError, IndexError):
            raise ValueError("Invalid month format. Use 'N months' (e.g., '6 months').")
    else:
        try:
            datetime.strptime(cutoff, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date format. Use 'YYYY-MM-DD' or 'N months'.")
    return cutoff

def validate_cleanup_months(months: int) -> int:
    """Validate cleanup months."""
    if months <= 0:
        raise ValueError("Cleanup months must be positive.")
    return months

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Validate channel URLs
    total_tests += 1
    try:
        urls = validate_channel_urls("https://www.youtube.com/@TrelisResearch")
        if not urls == ["https://www.youtube.com/@TrelisResearch"]:
            all_validation_failures.append("Channel URL validation incorrect")
    except Exception as e:
        all_validation_failures.append(f"Channel URL validation failed: {str(e)}")

    # Test 2: Validate date cutoff
    total_tests += 1
    try:
        cutoff = validate_date_cutoff("2025-01-01")
        if cutoff != "2025-01-01":
            all_validation_failures.append("Date cutoff validation incorrect")
    except Exception as e:
        all_validation_failures.append(f"Date cutoff validation failed: {str(e)}")

    # Test 3: Validate cleanup months
    total_tests += 1
    try:
        months = validate_cleanup_months(12)
        if months != 12:
            all_validation_failures.append("Cleanup months validation incorrect")
    except Exception as e:
        all_validation_failures.append(f"Cleanup months validation failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
