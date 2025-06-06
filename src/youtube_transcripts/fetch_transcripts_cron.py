"""
Module: fetch_transcripts_cron.py
Description: Functions for fetch transcripts cron operations

External Dependencies:
- sqlite3: [Documentation URL]
- youtube_transcript_api: [Documentation URL]
- pytube: [Documentation URL]
- core: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/fetch_transcripts_cron.py
import sqlite3
import os
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from pytube import Channel
from datetime import datetime, timedelta
import sys
import time
from core.database import initialize_database, check_transcript_exists, store_transcript, cleanup_old_transcripts
from core.transcript import get_channel_videos, get_transcript, enhance_transcript, parse_date_cutoff

# Configuration
DB_PATH = "youtube_transcripts.db"
CHANNEL_URLS = [
    "https://www.youtube.com/@TrelisResearch",
]
DATE_CUTOFF = "1 month"

def main():
    """Fetch and store transcripts for cron execution."""
    initialize_database()
    date_cutoff = parse_date_cutoff(DATE_CUTOFF)
    print(f"Fetching transcripts for videos newer than {date_cutoff.strftime('%Y-%m-%d')}")
    
    # Cleanup old transcripts
    deleted = cleanup_old_transcripts(max_age_months=12)
    print(f"Deleted {deleted} transcripts older than 12 months.")
    
    # Fetch transcripts, skipping summaries to reduce API costs
    for channel_url in CHANNEL_URLS:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM video_metadata WHERE channel_name = ?", (Channel(channel_url).channel_name or "Unknown Channel",))
        transcript_count = cursor.fetchone()[0]
        conn.close()
        
        if transcript_count > 0:
            print(f"Found {transcript_count} existing transcripts for channel {channel_url}. Checking for new videos.")
        
        videos = get_channel_videos(channel_url, date_cutoff)
        channel_name = Channel(channel_url).channel_name or "Unknown Channel"
        for video_id, title, publish_date in videos:
            if check_transcript_exists(video_id):
                print(f"Skipping existing video: {title}")
                continue
            
            transcript = get_transcript(video_id)
            if transcript:
                summary = "Summary skipped for cron run."
                enhanced_transcript = enhance_transcript(transcript)
                store_transcript(video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript)
                print(f"Stored transcript for video: {title}")
            else:
                print(f"No transcript available for video: {title}")

if __name__ == "__main__":
    main()
