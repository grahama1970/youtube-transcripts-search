"""
Module: unified_search.py
Description: Implementation of unified search functionality

External Dependencies:
- youtube_transcripts: [Documentation URL]
- : [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/src/youtube_transcripts/unified_search.py
"""
Unified search system integrating:
- DeepRetrieval for VERL-based query optimization
- Local Ollama models for inference
- Unsloth LoRA adapters for fine-tuning
- ArangoDB for graph-based knowledge management

External Dependencies:
- See individual module dependencies in split files

Example Usage:
>>> from unified_search import UnifiedYouTubeSearch
>>> from unified_search_config import UnifiedSearchConfig
>>> searcher = UnifiedYouTubeSearch(UnifiedSearchConfig())
>>> results = searcher.search("how to implement RAG")
>>> print(f"Found {len(results)} results")
"""

import logging
import sys
from typing import Any

# Add paths for companion projects
sys.path.extend([
    '/home/graham/workspace/experiments/unsloth_wip',
    '/home/graham/workspace/experiments/arangodb',
    '/home/graham/workspace/experiments/youtube_transcripts'
])

# Import from split modules
# Import core functionality
from youtube_transcripts.core.database import search_transcripts
from youtube_transcripts.search_widener import SearchWidener
from youtube_transcripts.youtube_search import QuotaExceededException, YouTubeSearchAPI, YouTubeSearchConfig

from .deepretrieval_optimizer import DeepRetrievalQueryOptimizer
from .graph_memory_integration import GraphMemoryIntegration
from .unified_search_config import UnifiedSearchConfig

logger = logging.getLogger(__name__)


class UnifiedYouTubeSearch:
    """
    Unified search interface combining all search capabilities
    """

    def __init__(self, config: UnifiedSearchConfig):
        self.config = config

        # Initialize components
        self.query_optimizer = DeepRetrievalQueryOptimizer(config)
        self.graph_memory = GraphMemoryIntegration(config)
        self.search_widener = SearchWidener()

        # Initialize YouTube search if enabled
        if config.youtube_search_enabled and config.youtube_api_key:
            youtube_config = YouTubeSearchConfig(
                api_key=config.youtube_api_key,
                max_results=config.youtube_max_results
            )
            self.youtube_api = YouTubeSearchAPI(youtube_config)
        else:
            self.youtube_api = None

    def search(
        self,
        query: str,
        channel_filter: str | None = None,
        use_optimization: bool = True,
        search_youtube: bool = False,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Perform unified search across all sources
        
        Args:
            query: User search query
            channel_filter: Optional channel name to filter
            use_optimization: Whether to use query optimization
            search_youtube: Whether to search YouTube API
            limit: Maximum results to return
            
        Returns:
            List of search results with metadata
        """
        results = []

        # Get query context from graph memory
        context = self.graph_memory.get_query_context()
        if channel_filter:
            context["channel_focus"] = channel_filter

        # Optimize query if enabled
        if use_optimization:
            optimization = self.query_optimizer.optimize_query(query, context)
            search_query = optimization["optimized"]
            logger.info(f"Optimized query: '{query}' -> '{search_query}'")
            logger.debug(f"Reasoning: {optimization.get('reasoning', 'N/A')}")
        else:
            search_query = query
            optimization = None

        # Search local database first
        try:
            # Pass channel filter as a list if specified
            channel_names = [channel_filter] if channel_filter else None
            db_results = search_transcripts(search_query, channel_names=channel_names, limit=limit)

            # Enrich results with metadata
            for result in db_results:
                # Get the transcript text (database returns as "transcript")
                transcript_text = result.get("transcript", result.get("content", ""))
                
                # Create snippet from transcript
                snippet = self._create_snippet(transcript_text, search_query)
                
                enriched = {
                    "source": "local_db",
                    "video_id": result.get("video_id"),
                    "title": result.get("title", ""),
                    "channel_name": result.get("channel_name", ""),
                    "content": transcript_text,
                    "transcript": transcript_text,  # Include both for compatibility
                    "snippet": snippet,
                    "url": f"https://youtube.com/watch?v={result.get('video_id', '')}",
                    "published_at": result.get("publish_date", result.get("published_at", "")),
                    "score": result.get("rank", result.get("score", 0.0))
                }

                # Apply channel filter if specified
                if channel_filter and enriched["channel_name"].lower() != channel_filter.lower():
                    continue

                results.append(enriched)

        except Exception as e:
            logger.error(f"Database search failed: {e}")

        # Search YouTube API if enabled and requested
        if search_youtube and self.youtube_api:
            try:
                youtube_results = self._search_youtube_api(search_query, channel_filter)

                # Merge YouTube results (avoiding duplicates)
                existing_ids = {r["video_id"] for r in results}
                for yt_result in youtube_results:
                    if yt_result["video_id"] not in existing_ids:
                        results.append(yt_result)

            except QuotaExceededException:
                logger.warning("YouTube API quota exceeded")
            except Exception as e:
                logger.error(f"YouTube search failed: {e}")

        # Widen search if not enough results
        if len(results) < 10 and use_optimization:
            logger.info(f"Only {len(results)} results found, widening search")
            widened = self.search_widener.search_with_widening(search_query)

            # Add widened search results
            if widened.results:
                try:
                    existing_ids = {r["video_id"] for r in results}

                    for result in widened.results:
                        if result.get("video_id") not in existing_ids:
                            # Get the transcript text (handle both field names)
                            transcript_text = result.get("transcript", result.get("content", ""))
                            
                            # Create snippet
                            snippet = self._create_snippet(transcript_text, search_query)
                            
                            enriched = {
                                "source": "widened_search",
                                "video_id": result.get("video_id"),
                                "title": result.get("title", ""),
                                "channel_name": result.get("channel_name", ""),
                                "content": transcript_text,
                                "transcript": transcript_text,  # Include both for compatibility
                                "snippet": snippet,
                                "url": f"https://youtube.com/watch?v={result.get('video_id', '')}",
                                "published_at": result.get("publish_date", result.get("published_at", "")),
                                "score": result.get("rank", result.get("score", 0.0)) * 0.8  # Slightly lower score for widened
                            }

                            if channel_filter and enriched["channel_name"].lower() != channel_filter.lower():
                                continue

                            results.append(enriched)
                            existing_ids.add(enriched["video_id"])

                except Exception as e:
                    logger.error(f"Widened search failed for '{variant}': {e}")

        # Sort by score (descending)
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Store search interaction in graph memory
        if optimization:
            self.graph_memory.store_search_interaction(
                query=query,
                results=results,
                optimized_query=search_query
            )

        # Extract relationships if we have multiple results
        if len(results) > 1 and self.graph_memory.enabled:
            self._extract_result_relationships(results[:10])  # Top 10 only

        # Return structured response
        return {
            'query': query,
            'optimized_query': search_query if use_optimization and optimization else query,
            'results': results[:limit],
            'total_found': len(results),
            'channels_searched': list(set(r.get('channel_name', '') for r in results if r.get('channel_name')))
        }

    def _search_youtube_api(self, query: str, channel_filter: str | None = None) -> list[dict[str, Any]]:
        """Search YouTube API and format results"""
        results = []

        if not self.youtube_api:
            return results

        # Search with channel filter if specified
        if channel_filter:
            # Try to find channel ID from our config
            channel_url = self.config.channels.get(channel_filter)
            if channel_url:
                # Extract channel handle/ID from URL
                channel_id = channel_url.split("@")[-1] if "@" in channel_url else None
                api_results = self.youtube_api.search_channel(query, channel_id)
            else:
                # General search with channel name in query
                api_results = self.youtube_api.search(f"{query} {channel_filter}")
        else:
            api_results = self.youtube_api.search(query)

        # Format YouTube API results
        for item in api_results:
            results.append({
                "source": "youtube_api",
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel_name": item["snippet"]["channelTitle"],
                "content": item["snippet"]["description"],  # Only description available
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                "published_at": item["snippet"]["publishedAt"],
                "score": 0.5  # Default score for API results
            })

        return results

    def _create_snippet(self, text: str, query: str, context_length: int = 150) -> str:
        """Create a snippet from text highlighting the query context"""
        if not text:
            return ""
        
        # Convert to lowercase for case-insensitive search
        text_lower = text.lower()
        query_lower = query.lower()
        
        # Find the position of the query in the text
        pos = text_lower.find(query_lower)
        
        if pos == -1:
            # If exact match not found, try to find any of the query words
            words = query_lower.split()
            for word in words:
                pos = text_lower.find(word)
                if pos != -1:
                    break
        
        if pos == -1:
            # No match found, return beginning of text
            return text[:context_length * 2] + "..." if len(text) > context_length * 2 else text
        
        # Calculate snippet boundaries
        start = max(0, pos - context_length)
        end = min(len(text), pos + len(query) + context_length)
        
        # Add ellipsis if needed
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        
        return prefix + text[start:end] + suffix

    def _extract_result_relationships(self, results: list[dict[str, Any]]):
        """Extract relationships between search results"""
        try:
            # Compare each pair of results
            for i in range(len(results)):
                for j in range(i + 1, len(results)):
                    relationships = self.graph_memory.extract_relationships_between_transcripts(
                        results[i],
                        results[j]
                    )

                    if relationships:
                        logger.debug(
                            f"Found {len(relationships)} relationships between "
                            f"'{results[i]['title'][:50]}...' and '{results[j]['title'][:50]}...'"
                        )

        except Exception as e:
            logger.error(f"Failed to extract relationships: {e}")

    def get_channels(self) -> dict[str, str]:
        """Get configured channels"""
        return self.config.channels

    def add_channel(self, name: str, url: str):
        """Add a new channel to configuration"""
        self.config.channels[name] = url


def example_unified_search():
    """Example usage of unified search"""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create configuration
    config = UnifiedSearchConfig()

    # Create unified searcher
    searcher = UnifiedYouTubeSearch(config)

    # Example searches
    queries = [
        "how to implement RAG with vector databases",
        "fine tuning llama 3.2 quantization",
        "multimodal embeddings CLIP",
    ]

    for query in queries:
        print(f"\n{'='*80}")
        print(f"Searching for: {query}")
        print(f"{'='*80}")

        # Search with optimization
        results = searcher.search(
            query=query,
            use_optimization=True,
            search_youtube=False,  # Set to True if you have API key
            limit=5
        )

        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   Channel: {result['channel_name']}")
            print(f"   Source: {result['source']}")
            print(f"   Score: {result['score']:.3f}")
            print(f"   URL: {result['url']}")

            # Show snippet of content
            content_preview = result['content'][:200].replace('\n', ' ')
            print(f"   Preview: {content_preview}...")


if __name__ == "__main__":
    example_unified_search()
