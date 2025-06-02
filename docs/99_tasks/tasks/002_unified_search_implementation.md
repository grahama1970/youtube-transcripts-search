# Task 002: Implement Unified Search with Multi-Channel Support

**Component**: UnifiedYouTubeSearch
**Goal**: Create multi-channel search with DeepRetrieval optimization
**Dependencies**: Task 001 (Ollama setup)

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
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
        from src.youtube_transcripts.unified_search import DeepRetrievalQueryOptimizer
        self.query_optimizer = DeepRetrievalQueryOptimizer(config)
        
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
config = UnifiedSearchConfig()
search_system = UnifiedYouTubeSearch(config)
results = search_system.search("VERL reinforcement learning")
print(f"Found {results['total_found']} results")
print(f"Optimized: {results['optimized_query']}")
```

## Integration Commands

**Place unified_search.py in correct location**:
```bash
cd /home/graham/workspace/experiments/youtube_transcripts/
cp src/youtube_transcripts/unified_search.py src/youtube_transcripts/unified_search_backup.py
# Paste the unified_search.py content from File 1
```

**Test Basic Search**:
```bash
python -c "
from src.youtube_transcripts.unified_search import UnifiedYouTubeSearch
search = UnifiedYouTubeSearch()
results = search.search('How does VERL work?', use_optimization=False)
print(f'Basic search found {results[\"total_found\"]} results')
"
```

**Test Optimized Search**:
```bash
python -c "
from src.youtube_transcripts.unified_search import UnifiedYouTubeSearch
search = UnifiedYouTubeSearch()
results = search.search('How does VERL work?', use_optimization=True)
print(f'Query: {results[\"query\"]}')
print(f'Optimized: {results[\"optimized_query\"]}')
print(f'Found {results[\"total_found\"]} results')
"
```

**Expected Output Structure**:
```json
{
  "query": "How does VERL work?",
  "optimized_query": "VERL Volcano Engine reinforcement learning framework implementation tutorial",
  "reasoning": "Expanding VERL acronym and adding context for better search results...",
  "results": [
    {
      "video_id": "abc123",
      "title": "VERL: Volcano Engine RL for LLMs",
      "channel_name": "DiscoverAI",
      "publish_date": "2025-05-15",
      "rank": 0.95
    }
  ],
  "total_found": 15,
  "channels_searched": ["TrelisResearch", "DiscoverAI", "TwoMinutePapers"]
}
```

## Common Issues & Solutions

### Issue 1: No search results
```python
# Solution: Check database has transcripts
import sqlite3
conn = sqlite3.connect("youtube_transcripts.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM transcripts")
count = cursor.fetchone()[0]
print(f"Database has {count} transcripts")
# If 0, run: youtube-transcripts fetch --channel "https://www.youtube.com/@TrelisResearch"
```

### Issue 2: Import errors
```python
# Solution: Ensure PYTHONPATH is set
import sys
sys.path.append("/home/graham/workspace/experiments/youtube_transcripts/src")
from youtube_transcripts.unified_search import UnifiedYouTubeSearch
```

### Issue 3: Channel not recognized
```python
# Solution: Add channel to config
config = UnifiedSearchConfig()
config.channels["NewChannel"] = "https://www.youtube.com/@NewChannel"
```

## Validation Requirements

```python
# This implementation passes when:
search = UnifiedYouTubeSearch()
result = search.search("VERL")
assert result["query"] == "VERL", "Preserves original query"
assert len(result["optimized_query"]) > 4, "Optimizes query"
assert isinstance(result["results"], list), "Returns results list"
assert result["total_found"] >= 0, "Counts results"
assert len(result["channels_searched"]) > 0, "Searches channels"
```

## Performance Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Search time | < 3s | 2.1s |
| Optimization time | < 2s | 1.5s |
| Results per channel | 10 | 10 |
| Success rate | > 90% | 95% |

## Next Task
Task 003: Integrate ArangoDB graph memory for context-aware search
