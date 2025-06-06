"""
Module: youtube_search.py
Description: Implementation of youtube search functionality

External Dependencies:
- dataclasses: [Documentation URL]
- requests: https://requests.readthedocs.io/
- youtube_transcript_api: [Documentation URL]
- : [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/src/youtube_transcripts/youtube_search.py
"""
YouTube Data API v3 Search Integration
Implements full YouTube search capabilities with transcript fetching
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from .core.database import add_transcript
from .search_widener import SearchWidener

logger = logging.getLogger(__name__)

@dataclass
class YouTubeSearchResult:
    """Represents a YouTube search result"""
    video_id: str
    title: str
    channel_name: str
    channel_id: str
    publish_date: str
    description: str
    thumbnail_url: str

@dataclass
class YouTubeSearchConfig:
    """Configuration for YouTube API"""
    api_key: str
    max_results: int = 50  # Maximum allowed by API
    region_code: str = "US"
    language: str = "en"
    safe_search: str = "moderate"  # none, moderate, strict


class YouTubeSearchAPI:
    """
    Implements YouTube Data API v3 Search functionality
    
    Important: Each search costs 100 quota units
    Default quota is 10,000 units/day = 100 searches/day
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    SEARCH_QUOTA_COST = 100

    def __init__(self, config: YouTubeSearchConfig):
        self.config = config
        self.quota_used = 0
        self.daily_quota_limit = 10000

    def search_videos(
        self,
        query: str,
        max_results: int | None = None,
        order: str = "relevance",  # relevance, date, rating, title, viewCount
        published_after: datetime | None = None,
        published_before: datetime | None = None,
        channel_id: str | None = None,
        video_duration: str | None = None,  # short (<4min), medium (4-20min), long (>20min)
        video_definition: str | None = None,  # any, high, standard
        video_type: str | None = None,  # any, episode, movie
    ) -> list[YouTubeSearchResult]:
        """
        Search YouTube videos using the Data API v3
        
        Args:
            query: Search query string
            max_results: Number of results (max 50, costs same quota regardless)
            order: Sort order for results
            published_after: Filter by publish date
            published_before: Filter by publish date
            channel_id: Restrict to specific channel
            video_duration: Filter by duration
            video_definition: Filter by video quality
            video_type: Filter by video type
            
        Returns:
            List of YouTube search results
            
        Raises:
            QuotaExceededException: If daily quota exceeded
            YouTubeAPIException: For other API errors
        """

        # Check quota
        if self.quota_used + self.SEARCH_QUOTA_COST > self.daily_quota_limit:
            raise QuotaExceededException(
                f"Would exceed daily quota. Used: {self.quota_used}, "
                f"Cost: {self.SEARCH_QUOTA_COST}, Limit: {self.daily_quota_limit}"
            )

        # Build parameters
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results or self.config.max_results,
            'order': order,
            'regionCode': self.config.region_code,
            'relevanceLanguage': self.config.language,
            'safeSearch': self.config.safe_search,
            'key': self.config.api_key
        }

        # Add optional filters
        if published_after:
            params['publishedAfter'] = published_after.isoformat() + 'Z'
        if published_before:
            params['publishedBefore'] = published_before.isoformat() + 'Z'
        if channel_id:
            params['channelId'] = channel_id
        if video_duration:
            params['videoDuration'] = video_duration
        if video_definition:
            params['videoDefinition'] = video_definition
        if video_type:
            params['videoType'] = video_type

        # Make API request
        try:
            response = requests.get(
                f"{self.BASE_URL}/search",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            # Update quota usage
            self.quota_used += self.SEARCH_QUOTA_COST

            # Parse results
            data = response.json()
            results = []

            for item in data.get('items', []):
                snippet = item['snippet']
                results.append(YouTubeSearchResult(
                    video_id=item['id']['videoId'],
                    title=snippet['title'],
                    channel_name=snippet['channelTitle'],
                    channel_id=snippet['channelId'],
                    publish_date=snippet['publishedAt'][:10],  # YYYY-MM-DD
                    description=snippet['description'],
                    thumbnail_url=snippet['thumbnails']['high']['url']
                ))

            return results

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Likely quota exceeded
                raise QuotaExceededException(f"YouTube API quota exceeded: {e}")
            else:
                raise YouTubeAPIException(f"YouTube API error: {e}")
        except Exception as e:
            raise YouTubeAPIException(f"Failed to search YouTube: {e}")

    def search_with_transcripts(
        self,
        query: str,
        fetch_transcripts: bool = True,
        store_in_db: bool = True,
        **search_kwargs
    ) -> list[dict[str, Any]]:
        """
        Search YouTube and optionally fetch transcripts
        
        Args:
            query: Search query
            fetch_transcripts: Whether to fetch transcripts for results
            store_in_db: Whether to store transcripts in database
            **search_kwargs: Additional arguments for search_videos
            
        Returns:
            List of search results with optional transcript data
        """
        # Search videos
        search_results = self.search_videos(query, **search_kwargs)

        # Convert to dict format
        results = []
        for result in search_results:
            result_dict = {
                'video_id': result.video_id,
                'title': result.title,
                'channel_name': result.channel_name,
                'channel_id': result.channel_id,
                'publish_date': result.publish_date,
                'description': result.description,
                'thumbnail_url': result.thumbnail_url,
                'transcript': None,
                'transcript_available': False
            }

            # Optionally fetch transcript
            if fetch_transcripts:
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(result.video_id)
                    transcript_text = ' '.join([entry['text'] for entry in transcript_list])
                    result_dict['transcript'] = transcript_text
                    result_dict['transcript_available'] = True

                    # Store in database if requested
                    if store_in_db and transcript_text:
                        add_transcript(
                            video_id=result.video_id,
                            title=result.title,
                            channel_name=result.channel_name,
                            publish_date=result.publish_date,
                            transcript=transcript_text,
                            summary=result.description[:200]  # First 200 chars of description
                        )

                except Exception as e:
                    logger.warning(f"Could not fetch transcript for {result.video_id}: {e}")

            results.append(result_dict)

        return results

    def get_quota_status(self) -> dict[str, Any]:
        """Get current quota usage status"""
        return {
            'used': self.quota_used,
            'limit': self.daily_quota_limit,
            'remaining': self.daily_quota_limit - self.quota_used,
            'searches_remaining': (self.daily_quota_limit - self.quota_used) // self.SEARCH_QUOTA_COST
        }


class YouTubeSearchWithWidening:
    """
    Combines YouTube API search with progressive widening
    """

    def __init__(self, api_config: YouTubeSearchConfig):
        self.youtube_api = YouTubeSearchAPI(api_config)
        self.widener = SearchWidener()

    def search_with_fallback(
        self,
        query: str,
        min_results: int = 5,
        **search_kwargs
    ) -> dict[str, Any]:
        """
        Search YouTube with automatic query widening if needed
        
        Args:
            query: Search query
            min_results: Minimum acceptable results before widening
            **search_kwargs: Additional search parameters
            
        Returns:
            Dict with results and widening information
        """
        # Try original query
        results = self.youtube_api.search_videos(query, **search_kwargs)

        if len(results) >= min_results:
            return {
                'query': query,
                'final_query': query,
                'results': results,
                'widening_used': False,
                'widening_info': None
            }

        # Not enough results, try widening
        widening_result = self.widener.search_with_widening(query)

        # If widening found a better query, search YouTube with it
        if widening_result.final_query != query:
            try:
                widened_results = self.youtube_api.search_videos(
                    widening_result.final_query,
                    **search_kwargs
                )

                if len(widened_results) > len(results):
                    return {
                        'query': query,
                        'final_query': widening_result.final_query,
                        'results': widened_results,
                        'widening_used': True,
                        'widening_info': {
                            'technique': widening_result.widening_technique,
                            'level': widening_result.widening_level,
                            'explanation': widening_result.explanation
                        }
                    }
            except QuotaExceededException:
                # Can't do another search, return original results
                pass

        # Return original results
        return {
            'query': query,
            'final_query': query,
            'results': results,
            'widening_used': False,
            'widening_info': None
        }


# Custom exceptions
class YouTubeAPIException(Exception):
    """Base exception for YouTube API errors"""
    pass

class QuotaExceededException(YouTubeAPIException):
    """Raised when API quota is exceeded"""
    pass


# Example usage
def demo_youtube_search():
    """Demonstrate YouTube search functionality"""

    # Get API key from environment or config
    api_key = os.environ.get('YOUTUBE_API_KEY', 'YOUR_API_KEY_HERE')

    if api_key == 'YOUR_API_KEY_HERE':
        print("Please set YOUTUBE_API_KEY environment variable")
        return

    config = YouTubeSearchConfig(api_key=api_key)
    youtube_search = YouTubeSearchWithWidening(config)

    # Search for VERL videos
    print("Searching YouTube for 'VERL volcano engine'...")
    result = youtube_search.search_with_fallback(
        query="VERL volcano engine reinforcement learning",
        min_results=5,
        max_results=10,
        order="relevance"
    )

    print(f"\nQuery: {result['query']}")
    print(f"Final query: {result['final_query']}")
    print(f"Results found: {len(result['results'])}")

    if result['widening_used']:
        print(f"Widening used: {result['widening_info']['technique']}")
        print(f"Explanation: {result['widening_info']['explanation']}")

    # Show results
    for i, video in enumerate(result['results'][:5]):
        print(f"\n{i+1}. {video.title}")
        print(f"   Channel: {video.channel_name}")
        print(f"   Published: {video.publish_date}")
        print(f"   Video ID: {video.video_id}")

    # Show quota status
    quota = youtube_search.youtube_api.get_quota_status()
    print(f"\nQuota used: {quota['used']}/{quota['limit']}")
    print(f"Searches remaining today: {quota['searches_remaining']}")


if __name__ == "__main__":
    demo_youtube_search()
