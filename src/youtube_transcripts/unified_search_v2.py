# youtube_transcripts/src/youtube_transcripts/unified_search_v2.py
"""
Unified search system with multi-channel support and DeepRetrieval optimization
Following Task 002 implementation requirements
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from youtube_transcripts.core.database import search_transcripts

@dataclass
class UnifiedSearchConfig:
    ollama_model: str = "qwen2.5:3b"
    channels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = {
                "TrelisResearch": "https://www.youtube.com/@TrelisResearch",
                "DiscoverAI": "https://www.youtube.com/@code4AI",
                "TwoMinutePapers": "https://www.youtube.com/@TwoMinutePapers",
            }

class UnifiedYouTubeSearch:
    def __init__(self, config: UnifiedSearchConfig = None):
        self.config = config or UnifiedSearchConfig()
        from src.youtube_transcripts.unified_search_enhanced import EnhancedDeepRetrievalOptimizer
        self.query_optimizer = EnhancedDeepRetrievalOptimizer(self.config.ollama_model)
        
    def search(
        self, 
        query: str, 
        channels: Optional[List[str]] = None,
        use_optimization: bool = True
    ) -> Dict[str, Any]:
        # Step 1: Optimize query
        optimization_result = {"optimized": query, "reasoning": ""}
        if use_optimization:
            optimization_result = self.query_optimizer.optimize_query(query)
        
        # Step 2: Search across channels
        search_query = optimization_result["optimized"]
        all_results = []
        search_channels = channels or list(self.config.channels.keys())
        
        for channel in search_channels:
            channel_results = search_transcripts(
                query=search_query,
                channel_names=[channel],
                limit=10
            )
            all_results.extend(channel_results)
        
        # Step 3: Sort by relevance
        all_results.sort(key=lambda x: x.get("rank", 0), reverse=True)
        
        return {
            "query": query,
            "optimized_query": search_query,
            "reasoning": optimization_result.get("reasoning", ""),
            "results": all_results[:20],
            "total_found": len(all_results),
            "channels_searched": search_channels
        }

# Test unified search
if __name__ == "__main__":
    config = UnifiedSearchConfig()
    search_system = UnifiedYouTubeSearch(config)
    results = search_system.search("VERL reinforcement learning")
    print(f"Found {results['total_found']} results")
    print(f"Optimized: {results['optimized_query']}")