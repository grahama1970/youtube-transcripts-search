"""
Module: transcript.py
Description: Functions for transcript operations

External Dependencies:
- yt_dlp: [Documentation URL]
- youtube_transcript_api: [Documentation URL]
- : [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/core/transcript.py
import re
from datetime import datetime, timedelta

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from .database import add_transcript, cleanup_old_transcripts


def extract_video_id(url: str) -> str | None:
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*&v=([a-zA-Z0-9_-]{11})'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_channel_videos(channel_url: str, date_cutoff: datetime | None = None) -> list[dict[str, str]]:
    """Get all videos from a channel with optional date filtering using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }

        videos = []

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract channel info
            channel_info = ydl.extract_info(channel_url, download=False)

            if 'entries' not in channel_info:
                return []

            # Process each video in the channel
            for entry in channel_info['entries']:
                if not entry:
                    continue

                # Get video details
                video_id = entry.get('id')
                if not video_id:
                    continue

                # Parse publish date
                upload_date = entry.get('upload_date', '')
                if upload_date:
                    publish_date = datetime.strptime(upload_date, '%Y%m%d')
                    publish_date_str = publish_date.strftime('%Y-%m-%d')

                    # Skip if video is older than cutoff
                    if date_cutoff and publish_date < date_cutoff:
                        continue
                else:
                    publish_date_str = ''

                videos.append({
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'video_id': video_id,
                    'title': entry.get('title', ''),
                    'publish_date': publish_date_str,
                    'channel_name': entry.get('uploader', channel_info.get('uploader', ''))
                })

        return videos
    except Exception as e:
        print(f"Error accessing channel {channel_url}: {e}")
        return []

def fetch_transcript(video_id: str) -> str | None:
    """Fetch transcript for a video"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([entry['text'] for entry in transcript_list])
        return transcript
    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        return None

def process_channels(channel_urls: list[str], date_cutoff: str | None = None,
                    cleanup_months: int | None = None) -> tuple[int, int]:
    """Process multiple channels and store transcripts"""
    # Parse date cutoff
    cutoff_date = None
    if date_cutoff:
        if date_cutoff.endswith('months'):
            months = int(date_cutoff.split()[0])
            cutoff_date = datetime.now() - timedelta(days=months * 30)
        else:
            cutoff_date = datetime.strptime(date_cutoff, '%Y-%m-%d')

    # Cleanup old transcripts
    deleted_count = 0
    if cleanup_months:
        deleted_count = cleanup_old_transcripts(cleanup_months)

    # Process channels
    processed_count = 0
    for channel_url in channel_urls:
        videos = get_channel_videos(channel_url, cutoff_date)

        for video in videos:
            video_id = video['video_id']
            if not video_id:
                continue

            transcript = fetch_transcript(video_id)
            if transcript:
                add_transcript(
                    video_id=video_id,
                    title=video['title'],
                    channel_name=video['channel_name'],
                    publish_date=video['publish_date'],
                    transcript=transcript
                )
                processed_count += 1

    return processed_count, deleted_count
