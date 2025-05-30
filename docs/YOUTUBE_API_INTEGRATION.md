# YouTube Data API v3 Integration Guide

## Overview

The YouTube Transcripts system now includes full YouTube Data API v3 search integration, allowing you to search across ALL of YouTube (not just pre-indexed transcripts).

## Key Features

### 1. Full YouTube Search
- Search entire YouTube catalog
- Filter by channel, date, duration, video type
- Sort by relevance, date, rating, title, or view count
- Automatic transcript fetching for search results

### 2. Quota Management
- Default quota: 10,000 units/day
- Each search costs 100 units (= 100 searches/day)
- Quota tracking and status reporting
- Graceful handling of quota exceeded errors

### 3. Search Parameters

```python
search_youtube_api(
    query="VERL volcano engine",          # Search query
    max_results=50,                       # Up to 50 results
    fetch_transcripts=True,               # Auto-fetch transcripts
    store_transcripts=True,               # Store in local DB
    published_after=datetime(2024, 1, 1), # Date filter
    channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw", # Channel filter
    use_optimization=True                 # Query optimization
)
```

### 4. Progressive Search Widening
When YouTube API returns few results, the system automatically:
1. Expands query with synonyms
2. Applies word stemming
3. Uses fuzzy matching
4. Adds semantic expansions

## Setup

### 1. Get YouTube API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable YouTube Data API v3
4. Create credentials (API Key)
5. Restrict key to YouTube Data API v3

### 2. Configure Environment
```bash
export YOUTUBE_API_KEY="your-api-key-here"
```

### 3. Use in Code
```python
from youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig

# Configure with API key
config = UnifiedSearchConfig(
    youtube_api_key="your-api-key",  # Or from env
    youtube_search_enabled=True,
    youtube_max_results=50
)

# Create search instance
search = UnifiedYouTubeSearch(config)

# Search YouTube
results = search.search_youtube_api(
    query="reinforcement learning tutorial",
    fetch_transcripts=True,
    store_transcripts=True
)

# Check results
print(f"Found {results['total_found']} videos")
print(f"Quota used: {results['quota_status']['used']}/{results['quota_status']['limit']}")

for video in results['results']:
    print(f"{video['title']} - {video['channel_name']}")
    if video['transcript_available']:
        print(f"  Transcript: {video['transcript'][:200]}...")
```

## Search Strategies

### 1. Local First (Default)
Search local database first, only query YouTube if needed:
```python
# Search local DB first
results = search.search(query="VERL", search_youtube=False)

# If not enough results, search YouTube
if results['total_found'] < 5:
    youtube_results = search.search_youtube_api(query="VERL")
```

### 2. YouTube First
For fresh content, search YouTube directly:
```python
# Get latest videos from YouTube
results = search.search_youtube_api(
    query="VERL volcano engine",
    published_after=datetime.now() - timedelta(days=7),  # Last week
    fetch_transcripts=True
)
```

### 3. Hybrid Search
Combine local and YouTube results:
```python
# Search both sources
local_results = search.search(query="VERL")
youtube_results = search.search_youtube_api(query="VERL", max_results=10)

# Combine and deduplicate
all_results = local_results['results'] + youtube_results['results']
unique_results = {r['video_id']: r for r in all_results}.values()
```

## Quota Optimization

### Best Practices
1. **Use max_results=50** - Same quota cost for 1 or 50 results
2. **Cache results** - Store transcripts locally to avoid repeat searches
3. **Batch queries** - Combine related searches when possible
4. **Monitor quota** - Check status before heavy usage

### Quota Status
```python
status = search.youtube_api.get_quota_status()
print(f"Searches remaining today: {status['searches_remaining']}")
```

## Advanced Filters

### Channel-Specific Search
```python
# Search only TechChannel videos
results = search.search_youtube_api(
    query="machine learning",
    channel_id="UCdJdEguB1F1CiYfgYVf7B3g"  # Channel ID
)
```

### Duration Filters
```python
# Only long videos (>20 minutes)
results = search.search_youtube_api(
    query="reinforcement learning",
    video_duration="long"  # short, medium, long
)
```

### Date Ranges
```python
# Videos from last month
from datetime import datetime, timedelta

results = search.search_youtube_api(
    query="VERL",
    published_after=datetime.now() - timedelta(days=30),
    published_before=datetime.now()
)
```

## Error Handling

### Quota Exceeded
```python
results = search.search_youtube_api(query="test")

if "error" in results:
    if results["error"] == "YouTube API quota exceeded":
        print(f"Quota exceeded. Try again tomorrow.")
        print(f"Current usage: {results['quota_status']}")
    else:
        print(f"Error: {results['error_details']}")
```

### Missing API Key
```python
if not search.youtube_api:
    print("YouTube search disabled - no API key configured")
    print("Set YOUTUBE_API_KEY environment variable")
```

## Integration with Search Widening

When YouTube returns few results, automatic widening kicks in:

```python
# Search with automatic widening
results = search.search_youtube_api(
    query="VERL",  # Might be expanded to "Volcano Engine Reinforcement Learning"
    use_optimization=True
)

if results['optimized_query'] != results['original_query']:
    print(f"Query expanded: {results['original_query']} → {results['optimized_query']}")
```

## Transcript Storage

Fetched transcripts are automatically stored in the local database:

```python
# Fetch and store transcripts
results = search.search_youtube_api(
    query="machine learning",
    fetch_transcripts=True,    # Download transcripts
    store_transcripts=True     # Save to database
)

# Later, search locally without API calls
local_results = search.search(query="machine learning")
```

## Cost Considerations

- Each search: 100 quota units
- Default daily quota: 10,000 units
- Maximum searches/day: 100
- Cost per search: ~$0.00 (free tier)
- Additional quota: Request via Google form

## Conclusion

The YouTube API integration provides powerful search capabilities while managing quotas efficiently. Use it to:
- Find fresh content not in your database
- Search by specific channels or dates
- Automatically fetch and store transcripts
- Expand your transcript database over time