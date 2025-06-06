#!/usr/bin/env python3
"""
Module: simple_yt_transcript_dl.py
Description: Simple YouTube transcript downloader function with YouTube API integration

External Dependencies:
- youtube-transcript-api: https://pypi.org/project/youtube-transcript-api/
- google-api-python-client: https://pypi.org/project/google-api-python-client/
- loguru: https://pypi.org/project/loguru/
- python-dotenv: https://pypi.org/project/python-dotenv/
- linkify-it-py: https://pypi.org/project/linkify-it-py/
- tenacity: https://pypi.org/project/tenacity/

Sample Input:
>>> download_youtube_transcript("dQw4w9WgXcQ")
>>> download_youtube_transcript("https://www.youtube.com/watch?v=qD-Nniey5TM&t=324s")
>>> download_youtube_transcript("https://youtu.be/qD-Nniey5TM")

Expected Output:
>>> Transcript saved to /home/graham/workspace/experiments/youtube_transcripts/transcripts/Rick_Astley_Never_Gonna_Give_You_Up_Official_Video_transcript.txt

Example Usage:
>>> from simple_yt_transcript_dl import download_youtube_transcript
>>> download_youtube_transcript("qD-Nniey5TM")
"""

import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

from dotenv import load_dotenv, find_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import xml.etree.ElementTree as ET
from linkify_it import LinkifyIt
import validators
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep

# Load environment variables using dotenv's find method
# This will search for .env file in current and parent directories
load_dotenv(find_dotenv())

# Configure loguru
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>")


@dataclass
class ExtractedLink:
    """Represents an extracted link with metadata."""
    url: str
    link_type: str  # 'github' or 'arxiv'
    source: str  # 'video_author' or comment author name
    is_authoritative: bool  # True if from video author


def extract_video_id(video_url_or_id: str) -> str:
    """
    Extract video ID from various YouTube URL formats or return as-is if already an ID.
    
    Supported formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&t=123s
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/embed/VIDEO_ID
    - https://www.youtube-nocookie.com/embed/VIDEO_ID
    - VIDEO_ID (raw ID)
    """
    # Handle empty input
    if not video_url_or_id:
        return video_url_or_id
    
    # Strip URL fragments
    url_without_fragment = video_url_or_id.split('#')[0]
    
    # If it doesn't contain youtube domains, assume it's already an ID
    url_lower = url_without_fragment.lower()
    if "youtube.com" not in url_lower and "youtu.be" not in url_lower and "youtube-nocookie.com" not in url_lower:
        logger.debug(f"Input appears to be a video ID: {video_url_or_id}")
        return video_url_or_id
    
    # Patterns to match various YouTube URL formats (case-insensitive)
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&\n]+)',       # Standard watch URL
        r'(?:youtu\.be\/)([^?&\n]+)',                  # Shortened URL
        r'(?:youtube\.com\/embed\/)([^?&\n]+)',        # Embed URL
        r'(?:youtube-nocookie\.com\/embed\/)([^?&\n]+)', # No-cookie embed
        r'(?:youtube\.com\/v\/)([^?&\n]+)'             # Old embed format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_without_fragment, re.IGNORECASE)
        if match:
            video_id = match.group(1)
            logger.debug(f"Extracted video ID: {video_id} from URL: {video_url_or_id}")
            return video_id
    
    logger.error(f"Could not extract video ID from URL: {video_url_or_id}")
    raise ValueError(f"Could not extract video ID from URL: {video_url_or_id}")


def extract_links(text: str) -> Tuple[List[str], List[str]]:
    """
    Backward-compatible function for tests.
    Extract GitHub and arXiv links from text.
    
    Returns:
        Tuple of (github_links, arxiv_links)
    """
    extracted = extract_links_from_text(text, 'test', False)
    github_links = [link.url for link in extracted if link.link_type == 'github']
    arxiv_links = [link.url for link in extracted if link.link_type == 'arxiv']
    return github_links, arxiv_links


def extract_links_from_text(text: str, source: str, is_authoritative: bool = False) -> List[ExtractedLink]:
    """
    Extract GitHub repository links and arXiv paper links from text using linkify-it.
    
    Args:
        text: Text to extract links from
        source: Source of the text (e.g., 'video_author' or commenter name)
        is_authoritative: Whether this is from the video author
        
    Returns:
        List of ExtractedLink objects
    """
    # Initialize linkify-it
    linkify = LinkifyIt()
    
    # Find all links
    matches = linkify.match(text) or []
    
    extracted_links = []
    seen_urls = set()  # To avoid duplicates
    
    for match in matches:
        url = match.url
        
        # Normalize GitHub URLs to just owner/repo
        github_match = re.match(r'https?://github\.com/([\w-]+/[\w.-]+)', url, re.IGNORECASE)
        if github_match:
            canonical_url = f'https://github.com/{github_match.group(1)}'
            if canonical_url not in seen_urls:
                seen_urls.add(canonical_url)
                extracted_links.append(ExtractedLink(
                    url=canonical_url,
                    link_type='github',
                    source=source,
                    is_authoritative=is_authoritative
                ))
            continue
        
        # Check for arXiv links
        if 'arxiv.org' in url.lower():
            # Normalize to abs URL if it's a PDF link
            url = url.replace('/pdf/', '/abs/')
            # Ensure HTTPS
            if url.startswith('http://'):
                url = url.replace('http://', 'https://')
            if url not in seen_urls:
                seen_urls.add(url)
                extracted_links.append(ExtractedLink(
                    url=url,
                    link_type='arxiv',
                    source=source,
                    is_authoritative=is_authoritative
                ))
            continue
    
    # Also check for arXiv:XXXX.XXXX format
    arxiv_pattern = r'arXiv:\s*(\d+\.\d+(?:v\d+)?)'
    for match in re.finditer(arxiv_pattern, text, re.IGNORECASE):
        arxiv_id = match.group(1)
        arxiv_url = f'https://arxiv.org/abs/{arxiv_id}'
        if arxiv_url not in seen_urls:
            seen_urls.add(arxiv_url)
            extracted_links.append(ExtractedLink(
                url=arxiv_url,
                link_type='arxiv',
                source=source,
                is_authoritative=is_authoritative
            ))
    
    return extracted_links


def log_retry_attempt(retry_state):
    """Log retry attempts with user-friendly messages."""
    sleep_time = retry_state.next_action.sleep
    attempt = retry_state.attempt_number
    error = retry_state.outcome.exception() if retry_state.outcome else None
    
    if sleep_time >= 60:
        time_msg = f"{sleep_time / 60:.1f} minutes"
    else:
        time_msg = f"{sleep_time:.0f} seconds"
    
    if isinstance(error, HttpError) and hasattr(error, 'resp') and error.resp.status == 403:
        logger.warning(f"⏳ YouTube API quota exceeded (attempt {attempt}/3). Waiting {time_msg} before retrying...")
        print(f"\n⏳ YouTube API temporarily unavailable. Will retry in {time_msg}...\n")
    else:
        logger.info(f"⏳ Request failed (attempt {attempt}/3). Retrying in {time_msg}...")
        print(f"\n⏳ Temporary issue detected. Retrying in {time_msg}...\n")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(HttpError),
    before_sleep=log_retry_attempt
)
def get_video_info(video_id: str) -> Tuple[str, str, str, str, List[ExtractedLink]]:
    """
    Get video title, channel name, duration, description, and extracted links using YouTube API.
    Falls back to basic info if API is not available.
    
    Returns:
        Tuple of (title, channel, duration, description, extracted_links)
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    
    if not api_key:
        logger.warning("YouTube API key not found. Using video ID as filename.")
        return video_id, "Unknown Channel", "Unknown", "", []
    
    try:
        # Build YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Request video details
        request = youtube.videos().list(
            part='snippet,contentDetails',
            id=video_id
        )
        response = request.execute()
        
        if not response['items']:
            logger.error(f"Video not found: {video_id}")
            raise ValueError(f"Video not found: {video_id}")
        
        video = response['items'][0]
        title = video['snippet']['title']
        channel = video['snippet']['channelTitle']
        duration = video['contentDetails']['duration']  # Format: PT4M13S
        description = video['snippet'].get('description', '')
        
        # Extract links from description (these are authoritative)
        extracted_links = extract_links_from_text(description, 'video_author', is_authoritative=True)
        
        logger.info(f"Retrieved video info: '{title}' by {channel}")
        
        github_count = sum(1 for link in extracted_links if link.link_type == 'github')
        arxiv_count = sum(1 for link in extracted_links if link.link_type == 'arxiv')
        
        if github_count > 0:
            logger.info(f"Found {github_count} GitHub links in description")
        if arxiv_count > 0:
            logger.info(f"Found {arxiv_count} arXiv links in description")
        
        return title, channel, duration, description, extracted_links
        
    except HttpError as e:
        if e.resp.status == 403:
            logger.error("YouTube API quota exceeded or API key invalid")
            raise ValueError("YouTube API quota exceeded or API key invalid. Please check your API key.")
        else:
            logger.error(f"YouTube API error: {e}")
            raise
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(HttpError),
    before_sleep=log_retry_attempt
)
def get_video_comments(video_id: str, max_comments: int = 100) -> List[Tuple[str, str, List[ExtractedLink]]]:
    """
    Get comments from video and extract GitHub/arXiv links.
    
    Args:
        video_id: YouTube video ID
        max_comments: Maximum number of comments to fetch
        
    Returns:
        List of tuples: (author, comment_text, extracted_links)
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    
    if not api_key:
        logger.warning("YouTube API key not found. Cannot fetch comments.")
        return []
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        comments_data = []
        
        # Initial request
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(100, max_comments),  # API max is 100 per page
            textFormat="plainText"
        )
        
        while request and len(comments_data) < max_comments:
            try:
                response = request.execute()
                
                for item in response.get('items', []):
                    comment_snippet = item['snippet']['topLevelComment']['snippet']
                    author = comment_snippet['authorDisplayName']
                    text = comment_snippet['textDisplay']
                    
                    # Extract links from comment (not authoritative)
                    extracted_links = extract_links_from_text(text, author, is_authoritative=False)
                    
                    # Only include comments that have links
                    if extracted_links:
                        comments_data.append((author, text, extracted_links))
                    
                    if len(comments_data) >= max_comments:
                        break
                
                # Check if there are more pages
                if 'nextPageToken' in response and len(comments_data) < max_comments:
                    request = youtube.commentThreads().list(
                        part="snippet",
                        videoId=video_id,
                        maxResults=min(100, max_comments - len(comments_data)),
                        pageToken=response['nextPageToken'],
                        textFormat="plainText"
                    )
                else:
                    break
                    
            except HttpError as e:
                if e.resp.status == 403:
                    logger.warning("Comments disabled or quota exceeded")
                    break
                else:
                    logger.warning(f"Error fetching comments: {e}")
                    break
        
        logger.info(f"Fetched {len(comments_data)} comments with links")
        
        # Log link statistics
        all_links = [link for _, _, links in comments_data for link in links]
        github_count = sum(1 for link in all_links if link.link_type == 'github')
        arxiv_count = sum(1 for link in all_links if link.link_type == 'arxiv')
        
        if github_count > 0:
            logger.info(f"Found {github_count} GitHub links in comments")
        if arxiv_count > 0:
            logger.info(f"Found {arxiv_count} arXiv links in comments")
        
        return comments_data
        
    except Exception as e:
        logger.error(f"Error getting comments: {e}")
        return []


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters and ensuring filesystem compatibility.
    """
    # Handle empty input
    if not filename or not filename.strip():
        return "untitled"
    
    # Remove invalid filename characters (but keep spaces)
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, ' ')
    
    # Normalize whitespace (multiple spaces/tabs/newlines to single space)
    filename = ' '.join(filename.split())
    
    # Strip leading/trailing whitespace
    filename = filename.strip()
    
    # Handle empty result after cleaning
    if not filename:
        return "untitled"
    
    # Remove leading/trailing dots (hidden files on Unix)
    filename = filename.strip('.')
    
    # Prevent path traversal
    filename = filename.replace('..', '')
    
    # Handle Windows reserved names
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
        'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3',
        'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    if filename.upper() in reserved_names:
        filename = f"{filename}_file"
    
    # Truncate to 255 characters (common filesystem limit)
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename


def download_youtube_transcript(video_url_or_id: str, output_dir: Optional[Path] = None) -> str:
    """
    Download YouTube transcript and save to file with proper video title.
    
    Args:
        video_url_or_id: YouTube video URL or just the video ID
        output_dir: Optional output directory (defaults to transcripts folder)
    
    Returns:
        Path to the saved transcript file
    
    Raises:
        ValueError: If video ID cannot be extracted or video not found
        TranscriptsDisabled: If transcripts are disabled for the video
        NoTranscriptFound: If no transcript is available
    """
    logger.info(f"Starting transcript download for: {video_url_or_id}")
    
    # Extract video ID
    try:
        video_id = extract_video_id(video_url_or_id)
    except ValueError as e:
        logger.error(f"Failed to extract video ID: {e}")
        raise
    
    # Get video information
    try:
        title, channel, duration, description, author_links = get_video_info(video_id)
    except ValueError as e:
        logger.warning(f"Could not get video info from API: {e}")
        # Fall back to using video ID
        title = video_id
        channel = "Unknown Channel"
        duration = "Unknown"
        description = ""
        author_links = []
    
    # Set output directory
    if output_dir is None:
        output_dir = Path("/home/graham/workspace/experiments/youtube_transcripts/transcripts")
    elif isinstance(output_dir, str):
        output_dir = Path(output_dir)
    
    # Create directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Output directory: {output_dir}")
    
    # Retry configuration
    max_retries = 3
    retry_delay = 2  # seconds
    
    try:
        # Fetch the transcript
        logger.info(f"Fetching transcript for video: {title}")
        
        # First, check available transcripts
        available_languages = []
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_languages = [t.language_code for t in transcript_list]
            logger.debug(f"Available transcripts: {available_languages}")
            
            if not available_languages:
                error_msg = (
                    f"No transcripts available for '{title}'. "
                    "The video may not have captions enabled or they may be private."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
                
        except TranscriptsDisabled:
            error_msg = (
                f"Transcripts are disabled for '{title}'. "
                "The video owner has disabled captions for this video."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            logger.warning(f"Could not list transcripts: {e}")
            # Continue anyway - sometimes list fails but get works
        
        # Try to get the transcript with tenacity retries
        transcript_data = None
        last_error = None
        
        def log_transcript_retry(retry_state):
            """Log transcript retry attempts with helpful messages."""
            sleep_time = retry_state.next_action.sleep
            attempt = retry_state.attempt_number
            
            if sleep_time >= 60:
                time_msg = f"{sleep_time / 60:.1f} minutes"
            else:
                time_msg = f"{sleep_time:.0f} seconds"
            
            logger.info(f"⏳ Transcript fetch failed (attempt {attempt}/3). Retrying in {time_msg}...")
            print(f"\n⏳ YouTube transcript temporarily unavailable. Will retry in {time_msg}...")
            print(f"   This is common when YouTube rate-limits requests. Please be patient.\n")
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=5, max=60),
            retry=retry_if_exception_type((ET.ParseError, Exception)),
            before_sleep=log_transcript_retry
        )
        def fetch_transcript_with_retry():
            logger.debug(f"Fetching transcript for video {video_id}")
            return YouTubeTranscriptApi.get_transcript(video_id)
        
        try:
            transcript_data = fetch_transcript_with_retry()
            logger.success(f"Successfully fetched transcript")
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            # These are definitive errors - no point retrying
            last_error = e
            logger.error(f"Transcript not available: {e}")
        except Exception as e:
            last_error = e
            logger.error(f"Failed to fetch transcript after retries: {e}")
        
        # Check if we got the transcript
        if not transcript_data:
            if isinstance(last_error, ET.ParseError):
                error_msg = (
                    f"Failed to parse transcript data for '{title}' after {max_retries} attempts. \n\n"
                    "This error typically occurs due to:\n"
                    "1. YouTube temporarily returning empty responses (try again later)\n"
                    "2. YouTube blocking requests from cloud servers/VPNs\n"
                    "3. Rate limiting (wait a few minutes before retrying)\n\n"
                    "Solutions:\n"
                    "- Try running from a different network or personal computer\n"
                    "- Wait a few minutes and try again\n"
                    "- Use a different video that's known to have transcripts\n"
                    "- Check if the video actually has captions enabled on YouTube"
                )
            elif isinstance(last_error, (TranscriptsDisabled, NoTranscriptFound)):
                error_msg = (
                    f"No transcript available for '{title}'.\n\n"
                    "This video either:\n"
                    "- Has transcripts/captions disabled by the owner\n"
                    "- Never had captions uploaded or auto-generated\n"
                    "- Has private captions that can't be accessed\n\n"
                    "Try a different video that shows [CC] on YouTube."
                )
            else:
                error_msg = (
                    f"Failed to fetch transcript for '{title}' after {max_retries} attempts.\n"
                    f"Last error: {last_error}\n\n"
                    "This might be a temporary issue. Please try again later."
                )
            
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Combine the transcript into a single string with timestamps
        transcript_lines = []
        for entry in transcript_data:
            timestamp = f"[{entry['start']:.2f}]"
            text = entry['text'].replace('\n', ' ')
            transcript_lines.append(f"{timestamp} {text}")
        
        transcript_text = "\n".join(transcript_lines)
        
        # Get comments (optional)
        logger.info("Fetching comments to extract additional links...")
        comments = get_video_comments(video_id, max_comments=100)
        
        # Create filename from video title
        safe_filename = sanitize_filename(title)
        output_file = output_dir / f"{safe_filename}_transcript.txt"
        
        # Handle duplicate filenames
        counter = 1
        while output_file.exists():
            output_file = output_dir / f"{safe_filename}_transcript_{counter}.txt"
            counter += 1
        
        with open(output_file, "w", encoding="utf-8") as f:
            # Add metadata header
            f.write(f"# YouTube Transcript\n")
            f.write(f"# Title: {title}\n")
            f.write(f"# Channel: {channel}\n")
            f.write(f"# Video ID: {video_id}\n")
            f.write(f"# URL: https://www.youtube.com/watch?v={video_id}\n")
            f.write(f"# Duration: {duration}\n")
            f.write(f"# Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("#" * 70 + "\n\n")
            
            # Collect all links from author and comments
            all_links = list(author_links)  # Start with author's links
            
            # Add links from comments
            for author, comment, links in comments:
                all_links.extend(links)
            
            # Separate by type and authoritativeness
            github_author = [link for link in all_links if link.link_type == 'github' and link.is_authoritative]
            github_comments = [link for link in all_links if link.link_type == 'github' and not link.is_authoritative]
            arxiv_author = [link for link in all_links if link.link_type == 'arxiv' and link.is_authoritative]
            arxiv_comments = [link for link in all_links if link.link_type == 'arxiv' and not link.is_authoritative]
            
            # Remove duplicates while preserving first occurrence
            seen_urls = set()
            def dedupe_links(links):
                result = []
                for link in links:
                    if link.url not in seen_urls:
                        seen_urls.add(link.url)
                        result.append(link)
                return result
            
            github_author = dedupe_links(github_author)
            github_comments = dedupe_links(github_comments)
            arxiv_author = dedupe_links(arxiv_author)
            arxiv_comments = dedupe_links(arxiv_comments)
            
            # Write extracted links section
            if any([github_author, github_comments, arxiv_author, arxiv_comments]):
                f.write("## EXTRACTED LINKS\n\n")
                
                # GitHub repositories - author first
                if github_author or github_comments:
                    f.write("### GitHub Repositories:\n\n")
                    
                    if github_author:
                        f.write("**From Video Author (Authoritative):**\n")
                        for link in github_author:
                            f.write(f"- {link.url}\n")
                        f.write("\n")
                    
                    if github_comments:
                        f.write("**From Comments:**\n")
                        for link in github_comments:
                            f.write(f"- {link.url} (mentioned by {link.source})\n")
                        f.write("\n")
                
                # arXiv papers - author first
                if arxiv_author or arxiv_comments:
                    f.write("### arXiv Papers:\n\n")
                    
                    if arxiv_author:
                        f.write("**From Video Author (Authoritative):**\n")
                        for link in arxiv_author:
                            f.write(f"- {link.url}\n")
                        f.write("\n")
                    
                    if arxiv_comments:
                        f.write("**From Comments:**\n")
                        for link in arxiv_comments:
                            f.write(f"- {link.url} (mentioned by {link.source})\n")
                        f.write("\n")
                
                f.write("#" * 70 + "\n\n")
            
            # Add description if available
            if description:
                f.write("## VIDEO DESCRIPTION\n\n")
                f.write(description)
                f.write("\n\n" + "#" * 70 + "\n\n")
            
            # Add transcript
            f.write("## TRANSCRIPT\n\n")
            f.write(transcript_text)
            
            # Add comments with links (already filtered in get_video_comments)
            if comments:
                f.write("\n\n" + "#" * 70 + "\n\n")
                f.write("## COMMENTS WITH LINKS\n\n")
                for author, comment, links in comments:
                    f.write(f"**{author}:**\n")
                    f.write(f"{comment}\n")
                    
                    # Show which links this comment mentioned
                    github_links = [link.url for link in links if link.link_type == 'github']
                    arxiv_links = [link.url for link in links if link.link_type == 'arxiv']
                    
                    if github_links:
                        f.write("GitHub: " + ", ".join(github_links) + "\n")
                    if arxiv_links:
                        f.write("arXiv: " + ", ".join(arxiv_links) + "\n")
                    f.write("\n")
        
        logger.success(f"Transcript saved to {output_file}")
        print(f"✅ Transcript saved to {output_file}")
        return str(output_file)
        
    except ValueError:
        # Re-raise ValueError with our custom messages
        raise
        
    except Exception as e:
        error_msg = (
            f"Unexpected error downloading transcript for '{title}': {e}\n\n"
            "This might be a temporary issue or a problem with the YouTube API.\n"
            "Please try again later or check if the video URL is correct."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)


def main():
    """CLI entry point for direct script execution"""
    if len(sys.argv) < 2:
        print("Usage: python simple_yt_transcript_dl.py <video_url_or_id>")
        print("Example: python simple_yt_transcript_dl.py dQw4w9WgXcQ")
        print("Example: python simple_yt_transcript_dl.py https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=324s")
        print("Example: python simple_yt_transcript_dl.py https://youtu.be/dQw4w9WgXcQ")
        sys.exit(1)
    
    video_url_or_id = sys.argv[1]
    
    try:
        output_path = download_youtube_transcript(video_url_or_id)
        logger.success(f"Download completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Validation when run without arguments
    if len(sys.argv) == 1:
        logger.info("Running module validation")
        
        # Test URL extraction
        test_cases = [
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=324s", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        
        all_passed = True
        for input_val, expected in test_cases:
            try:
                result = extract_video_id(input_val)
                if result == expected:
                    logger.success(f"✅ Extract ID test passed: {input_val} -> {result}")
                else:
                    logger.error(f"❌ Extract ID test failed: {input_val} -> {result} (expected {expected})")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ Extract ID test failed with error: {input_val} -> {e}")
                all_passed = False
        
        # Test filename sanitization
        filename_tests = [
            ("How to Build AI Agents", "How_to_Build_AI_Agents"),
            ("Video: Part 1/2", "Video_Part_12"),
            ("Test | Multiple  Spaces", "Test_Multiple_Spaces"),
        ]
        
        for input_val, expected in filename_tests:
            result = sanitize_filename(input_val)
            if result == expected:
                logger.success(f"✅ Filename sanitization test passed: '{input_val}' -> '{result}'")
            else:
                logger.error(f"❌ Filename sanitization test failed: '{input_val}' -> '{result}' (expected '{expected}')") 
                all_passed = False
        
        if all_passed:
            print("✅ Module validation passed")
        else:
            print("❌ Module validation failed")
            sys.exit(1)
    else:
        # Run main function when arguments are provided
        main()
