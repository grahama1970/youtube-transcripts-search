#!/usr/bin/env python3
"""
Test the enhanced download_transcript.py with mock data to verify functionality.
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.download_transcript import (
    download_youtube_transcript,
    ExtractedLink
)


def test_full_functionality_with_mock():
    """Test the complete functionality with mock data."""
    
    # Mock video info with links
    mock_video_info = (
        "Deep Learning Tutorial",  # title
        "AI Researcher",          # channel
        "PT45M30S",              # duration
        """This video covers deep learning basics.
        
        Code available at: https://github.com/researcher/deep-learning-tutorial
        
        Based on the paper: https://arxiv.org/abs/2301.12345
        
        Additional resources at github.com/researcher/notebooks""",  # description
        [
            ExtractedLink(url="https://github.com/researcher/deep-learning-tutorial", 
                         link_type="github", source="video_author", is_authoritative=True),
            ExtractedLink(url="https://github.com/researcher/notebooks",
                         link_type="github", source="video_author", is_authoritative=True),
            ExtractedLink(url="https://arxiv.org/abs/2301.12345",
                         link_type="arxiv", source="video_author", is_authoritative=True),
        ]  # extracted links
    )
    
    # Mock transcript data
    mock_transcript = [
        {"start": 0.0, "text": "Welcome to this deep learning tutorial."},
        {"start": 3.5, "text": "Today we'll cover neural networks."},
        {"start": 7.2, "text": "Let's start with the basics."},
    ]
    
    # Mock comments with links
    mock_comments = [
        (
            "CodeEnthusiast",
            "Great tutorial! I implemented this in my repo: https://github.com/enthusiast/dl-implementation",
            [ExtractedLink(url="https://github.com/enthusiast/dl-implementation",
                          link_type="github", source="CodeEnthusiast", is_authoritative=False)]
        ),
        (
            "ResearchStudent", 
            "This relates to the recent paper arXiv:2302.98765 on transformers",
            [ExtractedLink(url="https://arxiv.org/abs/2302.98765",
                          link_type="arxiv", source="ResearchStudent", is_authoritative=False)]
        ),
    ]
    
    # Create test directory
    test_dir = Path("/tmp/test_youtube_transcripts")
    test_dir.mkdir(exist_ok=True)
    
    # Patch all external calls
    with patch('scripts.download_transcript.get_video_info') as mock_info:
        with patch('scripts.download_transcript.YouTubeTranscriptApi.list_transcripts') as mock_list:
            with patch('scripts.download_transcript.YouTubeTranscriptApi.get_transcript') as mock_get:
                with patch('scripts.download_transcript.get_video_comments') as mock_comm:
                    
                    # Configure mocks
                    mock_info.return_value = mock_video_info
                    
                    # Mock transcript list
                    mock_transcript_list = MagicMock()
                    mock_transcript_list.__iter__ = lambda self: iter([
                        MagicMock(language_code='en')
                    ])
                    mock_list.return_value = mock_transcript_list
                    
                    mock_get.return_value = mock_transcript
                    mock_comm.return_value = mock_comments
                    
                    # Run the download
                    output_path = download_youtube_transcript("test_video_id", test_dir)
                    
                    print(f"\n✅ Successfully created: {output_path}")
                    
                    # Read and display the file
                    with open(output_path, 'r') as f:
                        content = f.read()
                    
                    print("\n📄 File Contents:")
                    print("=" * 70)
                    print(content)
                    print("=" * 70)
                    
                    # Verify content
                    assert "Deep Learning Tutorial" in content
                    assert "AI Researcher" in content
                    
                    # Check links are properly categorized
                    assert "From Video Author (Authoritative):" in content
                    assert "https://github.com/researcher/deep-learning-tutorial" in content
                    assert "https://arxiv.org/abs/2301.12345" in content
                    
                    assert "From Comments:" in content
                    assert "https://github.com/enthusiast/dl-implementation" in content
                    assert "(mentioned by CodeEnthusiast)" in content
                    assert "https://arxiv.org/abs/2302.98765" in content
                    assert "(mentioned by ResearchStudent)" in content
                    
                    # Check transcript
                    assert "[0.00] Welcome to this deep learning tutorial." in content
                    assert "[3.50] Today we'll cover neural networks." in content
                    
                    # Check comments section
                    assert "COMMENTS WITH LINKS" in content
                    assert "CodeEnthusiast:" in content
                    assert "ResearchStudent:" in content
                    
                    print("\n✅ All verifications passed!")
                    
                    # Clean up
                    os.unlink(output_path)
                    
                    return True


if __name__ == "__main__":
    print("Testing enhanced YouTube transcript downloader with mock data...")
    success = test_full_functionality_with_mock()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)