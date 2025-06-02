"""
Unified Search v2 for YouTube Transcripts
Uses database adapter for dual SQLite/ArangoDB support

This module provides the main search interface that works with
both database backends transparently.

External Dependencies:
- Database adapter and configuration modules

Example Usage:
>>> from youtube_transcripts.unified_search_v2 import UnifiedSearchV2
>>> search = UnifiedSearchV2()
>>> results = await search.search("machine learning")
>>> print(f"Using {search.db.backend_type} backend")
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from .database_adapter import DatabaseAdapter
from .database_config import get_database_config, create_database_adapter
from .youtube_search import YouTubeSearcher
from .search_widener import SearchWidener

logger = logging.getLogger(__name__)


class UnifiedSearchV2:
    """
    Unified search interface supporting both SQLite and ArangoDB backends
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize unified search
        
        Args:
            config: Optional configuration override
        """
        # Get database adapter (auto-selects backend)
        self.db = create_database_adapter() if not config else DatabaseAdapter(config)
        
        # Get configuration
        self.config = get_database_config()
        
        # Initialize components
        self.youtube_api = self._init_youtube_api()
        self.search_widener = SearchWidener()
        
        logger.info(f"UnifiedSearchV2 initialized with {self.db.backend_type} backend")
        logger.info(f"Advanced features available: {self.db.has_advanced_features}")
    
    def _init_youtube_api(self) -> Optional[YouTubeSearcher]:
        """Initialize YouTube API if configured"""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if api_key:
            return YouTubeSearcher(api_key)
        return None
    
    async def search(self, query: str, 
                    limit: int = 10,
                    use_widening: bool = True,
                    filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search for transcripts with optional query widening
        
        Args:
            query: Search query
            limit: Maximum results
            use_widening: Enable progressive query widening
            filters: Optional filters (channel, date, etc.)
            
        Returns:
            Search results with metadata
        """
        # Try initial search
        results = await self.db.search(query, limit, filters)
        
        widening_info = None
        
        # If few results and widening enabled, try expanding query
        if use_widening and len(results) < 3:
            for level in range(1, 4):
                widened = self.search_widener.widen_query(query, level)
                expanded_results = await self.db.search(widened['query'], limit, filters)
                
                if len(expanded_results) > len(results):
                    results = expanded_results
                    widening_info = {
                        'original_query': query,
                        'expanded_query': widened['query'],
                        'level': level,
                        'method': widened['method'],
                        'explanation': f"Expanded search using {widened['method']}"
                    }
                    break
        
        return {
            'results': results,
            'total_results': len(results),
            'query': query,
            'widening_info': widening_info,
            'backend': self.db.backend_type,
            'advanced_features': self.db.has_advanced_features
        }
    
    async def search_youtube_api(self, query: str,
                               max_results: int = 50,
                               published_after: Optional[datetime] = None,
                               channel_id: Optional[str] = None,
                               fetch_transcripts: bool = False,
                               store_transcripts: bool = True) -> Dict[str, Any]:
        """
        Search YouTube API and optionally fetch/store transcripts
        
        Args:
            query: Search query
            max_results: Maximum results from API
            published_after: Filter by publish date
            channel_id: Filter by channel
            fetch_transcripts: Fetch transcripts for results
            store_transcripts: Store fetched transcripts
            
        Returns:
            YouTube API results
        """
        if not self.youtube_api:
            return {
                'error': 'YouTube API not configured',
                'items': []
            }
        
        # Search YouTube
        results = self.youtube_api.search(
            query=query,
            max_results=max_results,
            published_after=published_after,
            channel_id=channel_id
        )
        
        if fetch_transcripts and results.get('items'):
            # Fetch transcripts for each video
            for item in results['items']:
                video_id = item['id']['videoId']
                try:
                    transcript = self.youtube_api.get_transcript(video_id)
                    
                    if transcript and store_transcripts:
                        # Prepare video data for storage
                        video_data = {
                            'video_id': video_id,
                            'title': item['snippet']['title'],
                            'channel_name': item['snippet']['channelTitle'],
                            'channel_id': item['snippet']['channelId'],
                            'transcript': transcript,
                            'upload_date': item['snippet']['publishedAt'],
                            'description': item['snippet']['description'],
                            'metadata': {
                                'thumbnails': item['snippet']['thumbnails'],
                                'tags': item['snippet'].get('tags', [])
                            }
                        }
                        
                        # Store in database
                        await self.db.store_transcript(video_data)
                        item['transcript_stored'] = True
                    
                    item['transcript'] = transcript[:500] + "..." if len(transcript) > 500 else transcript
                    
                except Exception as e:
                    logger.error(f"Failed to fetch transcript for {video_id}: {e}")
                    item['transcript_error'] = str(e)
        
        return results
    
    async def find_evidence(self, claim: str, 
                          evidence_type: str = "both",
                          limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find evidence supporting or contradicting a claim
        
        Args:
            claim: The claim to find evidence for
            evidence_type: 'support', 'contradict', or 'both'
            limit: Maximum results
            
        Returns:
            List of evidence with confidence scores
        """
        return await self.db.find_evidence(claim, evidence_type)
    
    async def find_related(self, video_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find videos related to a given video
        
        Args:
            video_id: Source video ID
            limit: Maximum results
            
        Returns:
            List of related videos
        """
        return await self.db.find_related(video_id, limit)
    
    async def get_transcript(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific transcript
        
        Args:
            video_id: Video ID
            
        Returns:
            Transcript data or None
        """
        return await self.db.get_transcript(video_id)
    
    async def store_transcript(self, video_data: Dict[str, Any]) -> str:
        """
        Store a transcript
        
        Args:
            video_data: Video information including transcript
            
        Returns:
            Document ID
        """
        # Add scientific metadata if research features enabled
        if self.config.enable_research_features:
            video_data = await self._enrich_with_metadata(video_data)
        
        return await self.db.store_transcript(video_data)
    
    async def _enrich_with_metadata(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich video data with scientific metadata"""
        from .citation_detector import CitationDetector
        from .metadata_extractor import MetadataExtractor
        from .speaker_extractor import SpeakerExtractor
        
        transcript = video_data.get('transcript', '')
        
        # Extract citations
        detector = CitationDetector()
        citations = detector.detect_citations(transcript)
        video_data['citations'] = [
            {
                'type': c.type,
                'id': c.id,
                'text': c.text,
                'context': c.context,
                'confidence': c.confidence
            }
            for c in citations
        ]
        
        # Extract metadata
        extractor = MetadataExtractor()
        metadata = extractor.extract_entities(transcript)
        video_data['entities'] = metadata.get('entities', [])
        
        # Extract speakers
        speaker_extractor = SpeakerExtractor()
        speakers = speaker_extractor.extract_speakers(transcript)
        video_data['speakers'] = speakers
        
        return video_data
    
    @property
    def backend_info(self) -> Dict[str, Any]:
        """Get information about the current backend"""
        return {
            'type': self.db.backend_type,
            'has_advanced_features': self.db.has_advanced_features,
            'supports_embeddings': self.config.enable_embeddings and self.db.has_advanced_features,
            'supports_graph': self.config.enable_graph_features and self.db.has_advanced_features,
            'supports_research': self.config.enable_research_features
        }


# Maintain compatibility with existing code
class UnifiedYouTubeSearch(UnifiedSearchV2):
    """Compatibility wrapper for existing code"""
    
    def __init__(self, config=None):
        # Handle old-style config
        if hasattr(config, 'db_path'):
            new_config = {'backend': 'sqlite', 'sqlite_path': config.db_path}
            super().__init__(new_config)
        else:
            super().__init__(config)
    
    def search(self, query: str, **kwargs):
        """Synchronous wrapper for compatibility"""
        # Remove unsupported kwargs
        kwargs.pop('limit', None)  # Handle separately
        limit = kwargs.get('limit', 10)
        
        # Run async method
        return asyncio.run(super().search(query, limit=limit, **kwargs))


# Example usage
async def example_usage():
    """Example of using UnifiedSearchV2"""
    
    # Initialize with auto-detection
    search = UnifiedSearchV2()
    print(f"Using {search.backend_info['type']} backend")
    
    # Search local database
    results = await search.search("machine learning", limit=5)
    print(f"Found {results['total_results']} results")
    
    if results['widening_info']:
        print(f"Search was widened: {results['widening_info']['explanation']}")
    
    # Find evidence (advanced feature)
    if search.backend_info['supports_research']:
        evidence = await search.find_evidence(
            "Transformers are better than RNNs",
            evidence_type="both"
        )
        print(f"Found {len(evidence)} pieces of evidence")
    
    # Force SQLite backend
    sqlite_search = UnifiedSearchV2({'backend': 'sqlite'})
    print(f"SQLite backend: {sqlite_search.backend_info}")
    
    # Force ArangoDB backend (if available)
    try:
        arango_search = UnifiedSearchV2({'backend': 'arangodb'})
        print(f"ArangoDB backend: {arango_search.backend_info}")
    except ImportError:
        print("ArangoDB not available")


if __name__ == "__main__":
    import os
    asyncio.run(example_usage())