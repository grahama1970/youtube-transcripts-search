# youtube_transcripts/core/transcript.py
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from pytube import Channel
from datetime import datetime, timedelta
import time
from typing import List, Tuple, Optional
from pathlib import Path
from ..config import ADVANCED_INFERENCE_PATH

def get_channel_videos(channel_url: str, date_cutoff: datetime) -> List[Tuple[str, str, datetime]]:
    """Fetch video IDs, titles, and publish dates from a YouTube channel, filtered by date."""
    try:
        channel = Channel(channel_url)
        return [
            (video.video_id, video.title, video.publish_date)
            for video in channel.videos
            if video.publish_date and video.publish_date >= date_cutoff
        ]
    except Exception as e:
        print(f"Error fetching videos from {channel_url}: {e}")
        return []

def get_transcript(video_id: str) -> Optional[str]:
    """Fetch transcript for a given video ID with retry logic."""
    for attempt in range(3):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            return " ".join([entry['text'] for entry in transcript])
        except (TranscriptsDisabled, NoTranscriptFound):
            return None
        except Exception as e:
            print(f"Error fetching transcript for video {video_id} (attempt {attempt + 1}): {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

def enhance_transcript(transcript: str) -> str:
    """Enhance transcript using ADVANCED-inference (if available)."""
    try:
        if ADVANCED_INFERENCE_PATH.exists():
            import sys
            sys.path.append(str(ADVANCED_INFERENCE_PATH))
            from inference import advanced_inference
            return advanced_inference(transcript, mode="enhance", model="mistral-instruct-7b")
        return transcript
    except Exception as e:
        print(f"Error enhancing transcript: {e}")
        return transcript

def parse_date_cutoff(cutoff_str: str) -> datetime:
    """Parse date cutoff (e.g., '2025-01-01' or '6 months')."""
    try:
        if 'month' in cutoff_str.lower():
            months = int(cutoff_str.split()[0])
            return datetime.now() - timedelta(days=months * 30)
        return datetime.strptime(cutoff_str, '%Y-%m-%d')
    except Exception as e:
        print(f"Error parsing date cutoff: {e}. Using default (6 months).")
        return datetime.now() - timedelta(days=180)

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Parse date cutoff
    total_tests += 1
    try:
        cutoff = parse_date_cutoff("3 months")
        expected = datetime.now() - timedelta(days=90)
        if abs((cutoff - expected).days) > 1:
            all_validation_failures.append("Date cutoff parsing incorrect")
    except Exception as e:
        all_validation_failures.append(f"Date parsing failed: {str(e)}")

    # Test 2: Get transcript (mock video ID, expect None for invalid ID)
    total_tests += 1
    try:
        transcript = get_transcript("invalid_video_id")
        if transcript is not None:
            all_validation_failures.append("Expected None for invalid video ID")
    except Exception as e:
        all_validation_failures.append(f"Transcript fetch failed: {str(e)}")

    # Test 3: Enhance transcript
    total_tests += 1
    try:
        test_transcript = "This is a test."
        enhanced = enhance_transcript(test_transcript)
        if not isinstance(enhanced, str):
            all_validation_failures.append("Enhanced transcript not a string")
    except Exception as e:
        all_validation_failures.append(f"Enhance transcript failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
