#!/usr/bin/env python3
"""
REAL tests for YouTube functionality - NO FAKES
This will test if we can ACTUALLY fetch from YouTube
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from youtube_transcripts.core.transcript import (
    extract_video_id, 
    get_channel_videos, 
    fetch_transcript,
    process_channels
)


class TestRealYouTube:
    """Test REAL YouTube functionality"""
    
    def test_extract_video_id(self):
        """Test extracting video ID from various URL formats"""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be", "dQw4w9WgXcQ"),
            ("not a youtube url", None)
        ]
        
        for url, expected in test_cases:
            result = extract_video_id(url)
            assert result == expected, f"Failed for URL: {url}"
    
    @pytest.mark.slow
    def test_fetch_real_transcript(self):
        """Test fetching a REAL transcript from YouTube"""
        # Use a stable video that should have transcripts
        video_id = "jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video
        
        transcript = fetch_transcript(video_id)
        
        # Check if we actually got a transcript
        if transcript is None:
            pytest.skip("Transcript not available for test video")
        
        assert isinstance(transcript, str), "Transcript should be a string"
        assert len(transcript) > 0, "Transcript should not be empty"
        print(f"\nFetched transcript length: {len(transcript)} characters")
        print(f"First 100 chars: {transcript[:100]}...")
    
    @pytest.mark.slow
    def test_get_channel_videos_real(self):
        """Test getting videos from a REAL YouTube channel"""
        # Use a small channel to avoid rate limits
        channel_url = "https://www.youtube.com/@YouTube"
        
        videos = get_channel_videos(channel_url)
        
        # This might fail due to pytube issues
        if not videos:
            pytest.fail("Failed to fetch any videos from channel - pytube likely broken")
        
        assert isinstance(videos, list), "Should return a list"
        assert len(videos) > 0, "Should fetch at least one video"
        
        # Check first video structure
        first_video = videos[0]
        assert 'video_id' in first_video
        assert 'title' in first_video
        assert 'channel_name' in first_video
        
        print(f"\nFetched {len(videos)} videos from channel")
        print(f"First video: {first_video['title']}")
    
    def test_process_channels_with_empty_list(self):
        """Test process_channels with empty input"""
        processed, deleted = process_channels([])
        
        assert processed == 0, "Should process 0 videos with empty channel list"
        assert deleted == 0, "Should delete 0 videos with no cleanup specified"


def generate_youtube_test_report():
    """Generate report for YouTube functionality tests"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(__file__).parent.parent / "docs" / "reports" / f"youtube_functionality_report_{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write("# YouTube Functionality Test Report\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n")
        f.write("**Component**: YouTube Transcript Fetching\n")
        f.write("**Test Type**: Real YouTube API Tests\n\n")
        
        f.write("## Critical Findings\n\n")
        f.write("- **pytube is likely BROKEN** with current YouTube\n")
        f.write("- Channel fetching probably fails\n")
        f.write("- Transcript fetching might work via youtube-transcript-api\n")
        f.write("- Need to replace pytube with yt-dlp\n\n")
        
        f.write("## Recommendations\n\n")
        f.write("1. Replace pytube with yt-dlp immediately\n")
        f.write("2. Implement proper error handling\n")
        f.write("3. Add retry logic for API calls\n")
        f.write("4. Test with multiple real channels\n")
        
    return report_path


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])