#!/usr/bin/env python3
"""
Test YouTube API search functionality
Demonstrates searching YouTube and fetching transcripts
"""

from datetime import datetime, timedelta
from youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig

def test_youtube_search():
    """Test YouTube API search with the configured API key"""
    
    # Create config (will load API key from .env)
    config = UnifiedSearchConfig()
    
    # Check if API key was loaded
    if not config.youtube_api_key:
        print("ERROR: YouTube API key not found!")
        print("Please ensure YOUTUBE_API_KEY is set in .env file")
        return
    
    print(f"✓ YouTube API key loaded successfully")
    print(f"  Key: {config.youtube_api_key[:10]}...{config.youtube_api_key[-4:]}")
    
    # Create search instance
    search = UnifiedYouTubeSearch(config)
    
    # Test 1: Search for VERL videos
    print("\n=== Test 1: Searching for 'VERL volcano engine' ===")
    results = search.search_youtube_api(
        query="VERL volcano engine reinforcement learning",
        max_results=5,
        fetch_transcripts=True,
        store_transcripts=True
    )
    
    if "error" in results:
        print(f"Error: {results['error']}")
        print(f"Details: {results.get('error_details', 'No details')}")
    else:
        print(f"Found {results['total_found']} videos")
        print(f"Query used: {results['optimized_query']}")
        
        for i, video in enumerate(results['results'][:3]):
            print(f"\n{i+1}. {video['title']}")
            print(f"   Channel: {video['channel_name']}")
            print(f"   Published: {video['publish_date']}")
            print(f"   Has transcript: {video['transcript_available']}")
            if video['transcript']:
                print(f"   Transcript preview: {video['transcript'][:150]}...")
        
        # Show quota status
        quota = results['quota_status']
        print(f"\nQuota Status:")
        print(f"  Used: {quota['used']}/{quota['limit']}")
        print(f"  Remaining searches today: {quota['searches_remaining']}")
    
    # Test 2: Search recent videos only
    print("\n\n=== Test 2: Searching for recent AI videos (last 7 days) ===")
    results = search.search_youtube_api(
        query="artificial intelligence machine learning tutorial",
        max_results=5,
        published_after=datetime.now() - timedelta(days=7),
        fetch_transcripts=False  # Don't fetch transcripts to save time
    )
    
    if "error" not in results:
        print(f"Found {results['total_found']} recent videos")
        for i, video in enumerate(results['results'][:3]):
            print(f"\n{i+1}. {video['title']}")
            print(f"   Published: {video['publish_date']}")
            print(f"   Description: {video['description'][:100]}...")
    
    # Test 3: Search with channel filter
    print("\n\n=== Test 3: Channel-specific search ===")
    # Search for videos from a specific channel (example: Two Minute Papers)
    results = search.search_youtube_api(
        query="neural network",
        max_results=3,
        channel_id="UCbfYPyITQ-7l4upoX8nvctg",  # Two Minute Papers channel ID
        fetch_transcripts=False
    )
    
    if "error" not in results:
        print(f"Found {results['total_found']} videos from the channel")
        for video in results['results']:
            print(f"- {video['title']} ({video['publish_date']})")
    
    # Test 4: Combined local and YouTube search
    print("\n\n=== Test 4: Combined local DB + YouTube search ===")
    
    # First search local database
    local_results = search.search("VERL", use_optimization=False)
    print(f"Local DB results: {local_results['total_found']} videos")
    
    # If not enough local results, search YouTube
    if local_results['total_found'] < 5:
        print("Not enough local results, searching YouTube...")
        youtube_results = search.search_youtube_api(
            query="VERL volcano engine",
            max_results=10,
            fetch_transcripts=True,
            store_transcripts=True
        )
        
        if "error" not in youtube_results:
            print(f"Added {youtube_results['total_found']} videos from YouTube")
            print("These videos are now stored in the local database for future searches")
    
    # Final quota check
    if search.youtube_api:
        final_quota = search.youtube_api.get_quota_status()
        print(f"\n=== Final Quota Status ===")
        print(f"Total API calls made: {final_quota['used'] // 100}")
        print(f"Quota used: {final_quota['used']}/{final_quota['limit']}")
        print(f"Searches remaining today: {final_quota['searches_remaining']}")


if __name__ == "__main__":
    print("YouTube API Search Test")
    print("=" * 50)
    test_youtube_search()