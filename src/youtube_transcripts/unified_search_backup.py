# youtube_transcripts/src/youtube_transcripts/unified_search.py
"""
Unified search system integrating:
- DeepRetrieval for VERL-based query optimization
- Local Ollama models for inference
- Unsloth LoRA adapters for fine-tuning
- ArangoDB for graph-based knowledge management
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import json
import logging
from dataclasses import dataclass
import re

# Add paths for companion projects
sys.path.extend([
    '/home/graham/workspace/experiments/unsloth_wip',
    '/home/graham/workspace/experiments/arangodb',
    '/home/graham/workspace/experiments/youtube_transcripts'
])

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logging.warning("Ollama not available, install with: pip install ollama")

try:
    from arangodb.memory_bank import MemoryBank
    from arangodb.managers.conversation_manager import ConversationManager
    from arangodb.managers.knowledge_manager import KnowledgeGraphManager
    ARANGO_AVAILABLE = True
except ImportError:
    ARANGO_AVAILABLE = False
    logging.warning("ArangoDB not available, graph memory features disabled")

from youtube_transcripts.core.database import search_transcripts, add_transcript

logger = logging.getLogger(__name__)

@dataclass
class UnifiedSearchConfig:
    """Configuration for unified search system"""
    # Model configuration
    ollama_model: str = "qwen2.5:3b"  # Local model matching DeepRetrieval
    use_lora: bool = True
    lora_adapter_path: Optional[str] = "/home/graham/workspace/experiments/unsloth_wip/lora_model"
    
    # DeepRetrieval settings
    deepretrieval_endpoint: str = "http://localhost:8000"  # vLLM endpoint
    use_reasoning: bool = True  # Use <think> tags
    
    # ArangoDB settings
    arango_host: str = "http://localhost:8529"
    arango_db: str = "memory_bank"
    
    # Channel configuration
    channels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = {
                "TrelisResearch": "https://www.youtube.com/@TrelisResearch",
                "DiscoverAI": "https://www.youtube.com/@code4AI",
                "TwoMinutePapers": "https://www.youtube.com/@TwoMinutePapers",
                "YannicKilcher": "https://www.youtube.com/@YannicKilcher"
            }


class DeepRetrievalQueryOptimizer:
    """
    Integrates DeepRetrieval for query optimization
    Uses local Ollama models with optional LoRA adapters
    """
    
    def __init__(self, config: UnifiedSearchConfig):
        self.config = config
        if OLLAMA_AVAILABLE:
            self.ollama_client = ollama.Client()
        else:
            self.ollama_client = None
        
        # Initialize LoRA if available
        if config.use_lora and config.lora_adapter_path:
            self._load_lora_adapter()
    
    def _load_lora_adapter(self):
        """Load Unsloth LoRA adapter for the model"""
        try:
            from unsloth import FastLanguageModel
            
            # Load base model with LoRA
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.config.ollama_model,
                max_seq_length=2048,
                load_in_4bit=True,
                lora_path=self.config.lora_adapter_path
            )
            logger.info(f"Loaded LoRA adapter from {self.config.lora_adapter_path}")
        except Exception as e:
            logger.warning(f"Could not load LoRA adapter: {e}")
    
    def optimize_query(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Optimize query using DeepRetrieval methodology
        Returns optimized query with reasoning
        """
        if not OLLAMA_AVAILABLE or not self.ollama_client:
            # Fallback to simple optimization
            return {
                "original": user_query,
                "optimized": user_query + " tutorial implementation example",
                "reasoning": "Basic optimization (Ollama not available)"
            }
        
        # Build prompt with DeepRetrieval structure
        prompt = self._build_optimization_prompt(user_query, context)
        
        try:
            # Use Ollama for local inference
            response = self.ollama_client.chat(
                model=self.config.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
            )
            
            # Parse response with reasoning
            return self._parse_optimization_response(response['message']['content'])
            
        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            # Fallback to original query
            return {
                "original": user_query,
                "optimized": user_query,
                "reasoning": "Optimization failed, using original query"
            }
    
    def _build_optimization_prompt(self, query: str, context: Dict = None) -> str:
        """Build prompt following DeepRetrieval format"""
        context_str = ""
        if context:
            if "previous_queries" in context:
                context_str += f"\nPrevious queries: {context['previous_queries']}"
            if "channel_focus" in context:
                context_str += f"\nChannel focus: {context['channel_focus']}"
        
        return f"""You are a search query optimizer for YouTube transcripts.
Given a user query, generate an optimized search query that will retrieve the most relevant transcripts.

User query: "{query}"{context_str}

Generate your response in this format:
<think>
[Your reasoning about how to improve the query]
</think>
<answer>
[Your optimized query]
</answer>"""
    
    def _parse_optimization_response(self, response: str) -> Dict[str, Any]:
        """Parse response with reasoning tags"""
        # Extract reasoning
        think_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL)
        reasoning = think_match.group(1).strip() if think_match else ""
        
        # Extract optimized query
        answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
        optimized = answer_match.group(1).strip() if answer_match else response.strip()
        
        return {
            "optimized": optimized,
            "reasoning": reasoning,
            "original": response
        }


class GraphMemoryIntegration:
    """
    Integrates ArangoDB for graph-based memory and knowledge management
    """
    
    def __init__(self, config: UnifiedSearchConfig):
        self.config = config
        if ARANGO_AVAILABLE:
            try:
                self.memory_bank = MemoryBank()
                self.conversation_manager = ConversationManager(self.memory_bank.db)
                self.knowledge_manager = KnowledgeGraphManager(self.memory_bank.db)
                self.enabled = True
            except Exception as e:
                logger.warning(f"Could not initialize ArangoDB: {e}")
                self.enabled = False
        else:
            self.enabled = False
    
    def store_search_interaction(
        self, 
        query: str, 
        results: List[Dict], 
        optimized_query: str = None
    ) -> Optional[str]:
        """Store search interaction in memory bank"""
        if not self.enabled:
            return None
        
        try:
            # Create conversation memory
            memory_id = self.conversation_manager.create_memory(
                user_input=query,
                agent_response=f"Found {len(results)} results",
                metadata={
                    "optimized_query": optimized_query,
                    "result_count": len(results),
                    "result_ids": [r['video_id'] for r in results[:10]]
                }
            )
            
            # Extract and link entities
            entities = self._extract_entities_from_results(results)
            for entity in entities:
                self.knowledge_manager.create_entity(entity)
            
            return memory_id
        except Exception as e:
            logger.error(f"Failed to store search interaction: {e}")
            return None
    
    def get_query_context(self, user_id: str = "default") -> Dict[str, Any]:
        """Get context from previous searches"""
        if not self.enabled:
            return {}
        
        try:
            # Get recent memories
            recent = self.conversation_manager.search_memories(
                query="",
                user_id=user_id,
                limit=5
            )
            
            # Extract patterns
            previous_queries = [m.get('user_input', '') for m in recent]
            
            # Get related knowledge graph
            if previous_queries:
                graph_context = self.knowledge_manager.get_subgraph(
                    start_entity=previous_queries[0],
                    max_depth=2
                )
            else:
                graph_context = {}
            
            return {
                "previous_queries": previous_queries,
                "graph_context": graph_context,
                "user_patterns": self._analyze_user_patterns(recent)
            }
        except Exception as e:
            logger.error(f"Failed to get query context: {e}")
            return {}
    
    def _extract_entities_from_results(self, results: List[Dict]) -> List[Dict]:
        """Extract entities from search results"""
        entities = []
        
        for result in results[:5]:  # Top 5 results
            # Extract channel as entity
            entities.append({
                "name": result['channel_name'],
                "type": "youtube_channel",
                "properties": {"url": f"https://youtube.com/@{result['channel_name']}"}
            })
            
            # Extract key terms from title
            title_terms = result['title'].split()
            for term in title_terms:
                if len(term) > 4 and term[0].isupper():  # Simple heuristic
                    entities.append({
                        "name": term,
                        "type": "concept",
                        "properties": {"source": "video_title"}
                    })
        
        return entities
    
    def _analyze_user_patterns(self, memories: List[Dict]) -> Dict:
        """Analyze user search patterns"""
        channels = {}
        topics = {}
        
        for memory in memories:
            # Count channel preferences
            for result_id in memory.get('metadata', {}).get('result_ids', []):
                # Extract channel from result_id if stored
                pass
        
        return {
            "preferred_channels": channels,
            "common_topics": topics
        }


class UnifiedYouTubeSearch:
    """
    Main unified search system combining all components
    """
    
    def __init__(self, config: UnifiedSearchConfig = None):
        self.config = config or UnifiedSearchConfig()
        
        # Initialize components
        self.query_optimizer = DeepRetrievalQueryOptimizer(config)
        self.graph_memory = GraphMemoryIntegration(config)
        
        # Channel-specific search agents (can be specialized)
        self.channel_agents = {}
        
    def search(
        self, 
        query: str, 
        channels: Optional[List[str]] = None,
        user_id: str = "default",
        use_optimization: bool = True,
        use_memory: bool = True
    ) -> Dict[str, Any]:
        """
        Unified search across YouTube channels with all enhancements
        """
        # Step 1: Get context from memory if enabled
        context = {}
        if use_memory:
            context = self.graph_memory.get_query_context(user_id)
            logger.info(f"Retrieved context: {len(context.get('previous_queries', []))} previous queries")
        
        # Step 2: Optimize query if enabled
        optimization_result = {"optimized": query, "reasoning": ""}
        if use_optimization:
            if channels:
                context['channel_focus'] = channels
            optimization_result = self.query_optimizer.optimize_query(query, context)
            logger.info(f"Query optimized: '{query}' -> '{optimization_result['optimized']}'")
        
        # Step 3: Execute search with optimized query
        search_query = optimization_result['optimized']
        
        # Search across specified channels or all
        all_results = []
        search_channels = channels or list(self.config.channels.keys())
        
        for channel in search_channels:
            channel_results = search_transcripts(
                query=search_query,
                channel_names=[channel],
                limit=10
            )
            all_results.extend(channel_results)
        
        # Step 4: Re-rank results using graph context
        if use_memory and context.get('graph_context'):
            all_results = self._rerank_with_graph_context(all_results, context['graph_context'])
        
        # Step 5: Store interaction in memory
        if use_memory:
            memory_id = self.graph_memory.store_search_interaction(
                query=query,
                results=all_results,
                optimized_query=search_query
            )
        else:
            memory_id = None
        
        # Step 6: Generate Q&A pairs for future training
        qa_pairs = self._generate_qa_pairs(query, all_results)
        
        return {
            "query": query,
            "optimized_query": search_query,
            "reasoning": optimization_result.get('reasoning', ''),
            "results": all_results[:20],  # Top 20 results
            "total_found": len(all_results),
            "channels_searched": search_channels,
            "memory_id": memory_id,
            "qa_pairs": qa_pairs,
            "context_used": bool(context)
        }
    
    def _rerank_with_graph_context(
        self, 
        results: List[Dict], 
        graph_context: Dict
    ) -> List[Dict]:
        """Re-rank results based on knowledge graph connections"""
        # Simple boost for results connected to graph entities
        for result in results:
            boost = 0
            
            # Check if channel is in graph
            if result['channel_name'] in str(graph_context):
                boost += 0.2
            
            # Check for concept matches
            title_lower = result['title'].lower()
            for entity in graph_context.get('entities', []):
                if entity.lower() in title_lower:
                    boost += 0.1
            
            # Apply boost to ranking
            result['rank'] = result.get('rank', 0) + boost
        
        # Re-sort by new rank
        return sorted(results, key=lambda x: x.get('rank', 0), reverse=True)
    
    def _generate_qa_pairs(self, query: str, results: List[Dict]) -> List[Dict]:
        """Generate Q&A pairs for training data"""
        qa_pairs = []
        
        if results:
            # Generate based on top result
            top_result = results[0]
            qa_pairs.append({
                "question": query,
                "answer": f"Based on {top_result['channel_name']}'s video '{top_result['title']}', "
                          f"the key insight is: [extracted from transcript]",
                "source": top_result['video_id']
            })
        
        return qa_pairs
    
    def train_on_interactions(self, min_interactions: int = 100):
        """
        Train the search model on collected interactions
        Similar to DeepRetrieval's RL approach
        """
        if not self.graph_memory.enabled:
            logger.warning("Graph memory not available, cannot train on interactions")
            return
        
        # Get recent search interactions from memory
        recent_memories = self.graph_memory.conversation_manager.search_memories(
            query="",
            limit=min_interactions
        )
        
        if len(recent_memories) < min_interactions:
            logger.warning(f"Not enough interactions: {len(recent_memories)} < {min_interactions}")
            return
        
        # Prepare training data
        training_data = []
        for memory in recent_memories:
            if memory.get('metadata', {}).get('result_count', 0) > 0:
                reward = self._calculate_reward(memory)
                training_data.append({
                    "query": memory['user_input'],
                    "optimized": memory['metadata'].get('optimized_query', ''),
                    "reward": reward
                })
        
        # TODO: Implement actual RL training loop
        logger.info(f"Ready to train on {len(training_data)} interactions")
    
    def _calculate_reward(self, memory: Dict) -> float:
        """
        Calculate reward based on search effectiveness
        Following DeepRetrieval's reward structure
        """
        result_count = memory.get('metadata', {}).get('result_count', 0)
        
        # Reward structure similar to DeepRetrieval
        if result_count >= 10:
            return 5.0
        elif result_count >= 7:
            return 4.0
        elif result_count >= 5:
            return 3.0
        elif result_count >= 3:
            return 1.0
        elif result_count >= 1:
            return 0.5
        else:
            return -3.5


# Example usage function
def example_unified_search():
    """Example of using the unified search system"""
    
    # Initialize with custom configuration
    config = UnifiedSearchConfig(
        ollama_model="qwen2.5:3b",  # Use same model as DeepRetrieval
        use_lora=True,
        channels={
            "TrelisResearch": "https://www.youtube.com/@TrelisResearch",
            "DiscoverAI": "https://www.youtube.com/@code4AI",
            "TwoMinutePapers": "https://www.youtube.com/@TwoMinutePapers",
        }
    )
    
    # Create unified search system
    search_system = UnifiedYouTubeSearch(config)
    
    # Example 1: Search across all channels with optimization
    results = search_system.search(
        query="How does VERL volcano engine reinforcement learning work?",
        use_optimization=True,
        use_memory=True
    )
    
    print(f"Original query: {results['query']}")
    print(f"Optimized query: {results['optimized_query']}")
    print(f"Reasoning: {results['reasoning']}")
    print(f"Found {results['total_found']} results across {len(results['channels_searched'])} channels")
    
    # Example 2: Channel-specific search
    trelis_results = search_system.search(
        query="Monte Carlo tree search implementation",
        channels=["TrelisResearch"],
        use_optimization=True
    )
    
    # Example 3: Search with context from previous searches
    followup_results = search_system.search(
        query="Tell me more about the code implementation",
        user_id="graham",
        use_memory=True  # Will use context from previous searches
    )
    
    return results


if __name__ == "__main__":
    # Run example
    results = example_unified_search()
    
    # Display top results
    for i, result in enumerate(results['results'][:5]):
        print(f"\n{i+1}. {result['title']}")
        print(f"   Channel: {result['channel_name']}")
        print(f"   Date: {result['publish_date']}")
        print(f"   Rank: {result.get('rank', 'N/A')}")