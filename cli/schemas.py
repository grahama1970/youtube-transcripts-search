# youtube_transcripts/cli/schemas.py
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class Transcript(BaseModel):
    video_id: str
    title: str
    channel_name: str
    publish_date: str
    transcript: str
    enhanced_transcript: str
    rank: float

class QueryResult(BaseModel):
    answer: str
    videos: List[Transcript]

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Validate Transcript model
    total_tests += 1
    try:
        transcript = Transcript(
            video_id="test123",
            title="Test Video",
            channel_name="Test Channel",
            publish_date="2025-01-01",
            transcript="Test transcript",
            enhanced_transcript="Enhanced transcript",
            rank=-10.234
        )
        if not isinstance(transcript, Transcript):
            all_validation_failures.append("Transcript model validation failed")
    except Exception as e:
        all_validation_failures.append(f"Transcript model failed: {str(e)}")

    # Test 2: Validate QueryResult model
    total_tests += 1
    try:
        result = QueryResult(
            answer="Test answer",
            videos=[transcript]
        )
        if not isinstance(result, QueryResult):
            all_validation_failures.append("QueryResult model validation failed")
    except Exception as e:
        all_validation_failures.append(f"QueryResult model failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
