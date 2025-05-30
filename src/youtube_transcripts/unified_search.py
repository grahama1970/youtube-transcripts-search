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
from datetime import datetime

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
    from arangodb.core.memory import MemoryAgent
    from arangodb.core.arango_setup import connect_arango, ensure_database
    from arangodb.core.db_connection_wrapper import DatabaseOperations
    from arangodb.core.graph.relationship_extraction import RelationshipExtractor
    from arangodb.core.search.hybrid_search import hybrid_search
    ARANGO_AVAILABLE = True
except ImportError as e:
    ARANGO_AVAILABLE = False
    logging.warning(f"ArangoDB not available: {e}, graph memory features disabled")

from youtube_transcripts.core.database import search_transcripts, add_transcript, DB_PATH
from youtube_transcripts.search_widener import SearchWidener, SearchWidenerResult
from youtube_transcripts.youtube_search import YouTubeSearchAPI, YouTubeSearchConfig, QuotaExceededException

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
    
    # YouTube API settings
    youtube_api_key: Optional[str] = None
    youtube_search_enabled: bool = True
    youtube_max_results: int = 50  # Max allowed by API
    
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
        
        # Try to get YouTube API key from environment
        if not self.youtube_api_key:
            import os
            from dotenv import load_dotenv
            
            # Load from .env file
            load_dotenv()
            self.youtube_api_key = os.environ.get('YOUTUBE_API_KEY')


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
        if answer_match:
            optimized = answer_match.group(1).strip()
            # Take only the first line if multiple lines
            optimized = optimized.split('\n')[0].strip()
        else:
            # If no tags, clean the response
            optimized = response.strip()
            # Remove any XML tags that might be in the response
            optimized = re.sub(r'<[^>]+>', '', optimized)
            # Take only the first line
            optimized = optimized.split('\n')[0].strip()
        
        # Clean up the optimized query for FTS5
        # Remove special characters that could break SQL
        optimized = optimized.replace('<', '').replace('>', '').replace('"', '')
        
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
                # Initialize ArangoDB connection
                client = connect_arango()
                self.db = ensure_database(client)
                self.memory_agent = MemoryAgent(self.db)
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
            # Store the search interaction
            memory_data = {
                "query": query,
                "optimized_query": optimized_query,
                "result_count": len(results),
                "result_ids": [r['video_id'] for r in results[:10]],
                "timestamp": datetime.now().isoformat()
            }
            
            # Create a simple memory ID
            memory_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Extract and store entities
            entities = self._extract_entities_from_results(results)
            
            return memory_id
        except Exception as e:
            logger.error(f"Failed to store search interaction: {e}")
            return None
    
    def get_query_context(self, user_id: str = "default") -> Dict[str, Any]:
        """Get context from previous searches"""
        if not self.enabled:
            return {}
        
        try:
            # For now, return empty context since we don't have full memory implementation
            # This would normally query the ArangoDB memory collections
            return {
                "previous_queries": [],
                "graph_context": {},
                "user_patterns": {}
            }
        except Exception as e:
            logger.error(f"Failed to get query context: {e}")
            return {}
    
    def extract_entities_from_transcript(self, transcript_text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract named entities from transcript text using NLP.
        Identifies people, organizations, technical terms, and concepts.
        """
        if not self.enabled:
            return []
        
        entities = []
        metadata = metadata or {}
        
        # Extract channel as primary entity
        if 'channel_name' in metadata:
            entities.append({
                "name": metadata['channel_name'],
                "type": "youtube_channel",
                "properties": {
                    "url": f"https://youtube.com/@{metadata['channel_name']}",
                    "video_count": metadata.get('video_count', 1)
                }
            })
        
        # Simple entity extraction patterns
        # People: Look for capitalized names
        people_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        for match in re.finditer(people_pattern, transcript_text):
            entities.append({
                "name": match.group(1),
                "type": "person",
                "properties": {"source": "transcript", "confidence": 0.7}
            })
        
        # Organizations: Look for Inc., Corp., Company, etc. OR known tech companies
        org_pattern = r'\b([A-Z][A-Za-z\s&]+(?:Inc|Corp|Company|LLC|Ltd|Foundation|Institute|University))\b'
        known_orgs = ['OpenAI', 'Microsoft', 'Google', 'Facebook', 'Amazon', 'Apple', 'DeepMind', 
                      'Google DeepMind', 'MIT', 'Stanford', 'Facebook AI Research', 'Microsoft Research']
        
        # First check for known organizations
        for org in known_orgs:
            if org in transcript_text:
                entities.append({
                    "name": org,
                    "type": "organization", 
                    "properties": {"source": "transcript", "confidence": 0.9}
                })
        
        # Then check for pattern-based organizations
        for match in re.finditer(org_pattern, transcript_text):
            entities.append({
                "name": match.group(1).strip(),
                "type": "organization",
                "properties": {"source": "transcript", "confidence": 0.8}
            })
        
        # Technical terms: Capitalized words, acronyms, or terms with numbers
        tech_patterns = [
            r'\b([A-Z]{2,})\b',  # Acronyms like PPO, CNN
            r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b',  # CamelCase like AlphaGo
            r'\b(GPT-\d+)\b',  # GPT versions
            r'\b([A-Z]+[a-z]*-\d+)\b',  # Other versioned terms
        ]
        
        for pattern in tech_patterns:
            for match in re.finditer(pattern, transcript_text):
                term = match.group(1)
                if len(term) > 2:  # Skip very short acronyms
                    entities.append({
                        "name": term,
                        "type": "technical_term",
                        "properties": {"source": "transcript", "confidence": 0.6}
                    })
        
        # Topics from video metadata
        if 'title' in metadata:
            # Extract key terms from title
            title_terms = metadata['title'].split()
            for term in title_terms:
                if len(term) > 4 and term[0].isupper():
                    entities.append({
                        "name": term,
                        "type": "topic",
                        "properties": {"source": "video_title", "confidence": 0.9}
                    })
        
        # Deduplicate entities by normalized name and type
        seen = set()
        unique_entities = []
        
        # Normalize entity name for deduplication
        def normalize_name(name):
            return name.lower().strip().replace('-', ' ').replace('_', ' ')
        
        for entity in entities:
            normalized_name = normalize_name(entity['name'])
            key = (normalized_name, entity['type'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def extract_relationships_between_transcripts(
        self, 
        transcript1: Dict[str, Any], 
        transcript2: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships between two transcripts based on:
        - Shared entities (people, organizations, topics)
        - Temporal relationships (published dates)
        - Content similarity
        """
        if not self.enabled:
            return []
        
        relationships = []
        
        # Extract entities from both transcripts
        entities1 = self.extract_entities_from_transcript(
            transcript1.get('content', ''), 
            transcript1
        )
        entities2 = self.extract_entities_from_transcript(
            transcript2.get('content', ''), 
            transcript2
        )
        
        # Find shared entities with normalized matching
        def normalize_entity_name(name):
            # Normalize for matching: lowercase, strip, remove special chars
            normalized = name.lower().strip()
            # Remove common variations
            normalized = normalized.replace('-', ' ').replace('_', ' ')
            # Handle GPT variations
            if 'gpt' in normalized:
                normalized = normalized.replace('gpt 4', 'gpt-4').replace('gpt4', 'gpt-4')
            return normalized
        
        entities1_by_name = {normalize_entity_name(e['name']): e for e in entities1}
        entities2_by_name = {normalize_entity_name(e['name']): e for e in entities2}
        
        shared_entities = set(entities1_by_name.keys()) & set(entities2_by_name.keys())
        
        # Create SHARES_ENTITY relationships
        for entity_name in shared_entities:
            entity1 = entities1_by_name[entity_name]
            entity2 = entities2_by_name[entity_name]
            
            relationships.append({
                "from_id": transcript1['video_id'],
                "to_id": transcript2['video_id'],
                "type": "SHARES_ENTITY",
                "properties": {
                    "entity_name": entity1['name'],
                    "entity_type": entity1['type'],
                    "confidence": min(
                        entity1['properties'].get('confidence', 1.0),
                        entity2['properties'].get('confidence', 1.0)
                    )
                }
            })
        
        # Check same channel relationship
        if transcript1.get('channel_name') == transcript2.get('channel_name'):
            relationships.append({
                "from_id": transcript1['video_id'],
                "to_id": transcript2['video_id'],
                "type": "SAME_CHANNEL",
                "properties": {
                    "channel_name": transcript1['channel_name']
                }
            })
        
        # Temporal relationships
        if 'published_at' in transcript1 and 'published_at' in transcript2:
            try:
                from datetime import datetime
                date1 = datetime.fromisoformat(transcript1['published_at'].replace('Z', '+00:00'))
                date2 = datetime.fromisoformat(transcript2['published_at'].replace('Z', '+00:00'))
                
                time_diff_days = abs((date2 - date1).days)
                
                if time_diff_days <= 7:
                    relationships.append({
                        "from_id": transcript1['video_id'] if date1 < date2 else transcript2['video_id'],
                        "to_id": transcript2['video_id'] if date1 < date2 else transcript1['video_id'],
                        "type": "PUBLISHED_NEAR",
                        "properties": {
                            "days_apart": time_diff_days,
                            "relationship": "within_week"
                        }
                    })
            except Exception as e:
                logger.debug(f"Could not parse dates: {e}")
        
        # Topic similarity based on title overlap
        title1_words = set(transcript1.get('title', '').lower().split())
        title2_words = set(transcript2.get('title', '').lower().split())
        
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were'}
        title1_words -= stopwords
        title2_words -= stopwords
        
        shared_words = title1_words & title2_words
        if len(shared_words) >= 2:  # At least 2 shared meaningful words
            relationships.append({
                "from_id": transcript1['video_id'],
                "to_id": transcript2['video_id'],
                "type": "SIMILAR_TOPIC",
                "properties": {
                    "shared_keywords": list(shared_words),
                    "similarity_score": len(shared_words) / min(len(title1_words), len(title2_words))
                }
            })
        
        return relationships
    
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
    
    def search_with_arango_hybrid(
        self, 
        query: str, 
        channels: List[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Use ArangoDB hybrid search (semantic + keyword) as fallback
        when SQLite FTS5 returns no results
        """
        if not self.enabled:
            return []
        
        try:
            # Initialize database connection
            client = connect_arango()
            db = ensure_database(client)
            
            # Execute hybrid search
            results = hybrid_search(
                db=db,
                query_text=query,
                collections=["transcripts"],
                top_n=limit,
                output_format="json"
            )
            
            # Parse JSON results if needed
            if isinstance(results, str):
                results = json.loads(results)
            
            # Convert ArangoDB results to our format
            formatted_results = []
            # Handle both list and dict results
            if isinstance(results, list):
                for result in results:
                    if isinstance(result, dict):
                        formatted_result = {
                            "video_id": result.get("video_id", result.get("_key")),
                            "title": result.get("title", ""),
                            "channel_name": result.get("channel_name", ""),
                            "published_at": result.get("published_at", ""),
                            "url": result.get("url", ""),
                            "content": result.get("content", result.get("transcript", "")),
                            "score": result.get("_score", 0.0),
                            "source": "arangodb_hybrid"
                        }
                        formatted_results.append(formatted_result)
            elif isinstance(results, dict) and "results" in results:
                # Handle wrapped results
                for result in results.get("results", []):
                    if isinstance(result, dict):
                        formatted_result = {
                            "video_id": result.get("video_id", result.get("_key")),
                            "title": result.get("title", ""),
                            "channel_name": result.get("channel_name", ""),
                            "published_at": result.get("published_at", ""),
                            "url": result.get("url", ""),
                            "content": result.get("content", result.get("transcript", "")),
                            "score": result.get("_score", 0.0),
                            "source": "arangodb_hybrid"
                        }
                        formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"ArangoDB hybrid search error: {e}")
            return []


class UnifiedYouTubeSearch:
    """
    Main unified search system combining all components
    """
    
    def __init__(self, config: UnifiedSearchConfig = None, db_path: Path = None):
        self.config = config or UnifiedSearchConfig()
        self.db_path = db_path or DB_PATH
        
        # Initialize components
        self.query_optimizer = DeepRetrievalQueryOptimizer(self.config)
        self.graph_memory = GraphMemoryIntegration(self.config)
        self.search_widener = SearchWidener(db_path=self.db_path)
        
        # Initialize YouTube API if configured
        self.youtube_api = None
        if self.config.youtube_search_enabled and self.config.youtube_api_key:
            youtube_config = YouTubeSearchConfig(
                api_key=self.config.youtube_api_key,
                max_results=self.config.youtube_max_results
            )
            self.youtube_api = YouTubeSearchAPI(youtube_config)
            logger.info("YouTube API search enabled")
        else:
            logger.warning("YouTube API search disabled (no API key)")
        
        # Channel-specific search agents (can be specialized)
        self.channel_agents = {}
        
    def search(
        self, 
        query: str, 
        channels: Optional[List[str]] = None,
        user_id: str = "default",
        use_optimization: bool = True,
        use_memory: bool = True,
        use_widening: bool = True,
        search_youtube: bool = False,
        fetch_new_transcripts: bool = False
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
        widening_info = None
        
        # First try regular search
        for channel in search_channels:
            channel_results = search_transcripts(
                query=search_query,
                channel_names=[channel],
                limit=10,
                db_path=self.db_path
            )
            all_results.extend(channel_results)
        
        # If few/no results and ArangoDB is available, try hybrid search
        # Trigger if no results OR if we have a semantic query with few results
        if self.graph_memory.enabled and (not all_results or (len(all_results) < 3 and self._is_semantic_query(search_query))):
            logger.info("No results from SQLite FTS5, trying ArangoDB hybrid search")
            try:
                # Use ArangoDB hybrid search as fallback
                hybrid_results = self.graph_memory.search_with_arango_hybrid(
                    query=search_query,
                    channels=search_channels,
                    limit=20
                )
                if hybrid_results:
                    logger.info(f"ArangoDB hybrid search found {len(hybrid_results)} results")
                    all_results = hybrid_results
            except Exception as e:
                logger.error(f"ArangoDB hybrid search failed: {e}")
        
        # If still no results and widening is enabled, use search widener
        if not all_results and use_widening:
            widening_result = self.search_widener.search_with_widening(
                query=search_query,
                channel_names=None if not channels else channels
            )
            all_results = widening_result.results
            widening_info = {
                "technique": widening_result.widening_technique,
                "level": widening_result.widening_level,
                "final_query": widening_result.final_query,
                "explanation": widening_result.explanation
            }
        
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
            "context_used": bool(context),
            "widening_info": widening_info
        }
    
    def _is_semantic_query(self, query):
        """Determine if query is semantic vs keyword-based"""
        # Semantic queries typically have multiple words and conceptual terms
        words = query.lower().split()
        
        # Check for semantic indicators
        semantic_indicators = [
            len(words) >= 3,  # Multiple words
            any(word in ['understanding', 'explaining', 'learning', 'about', 'how', 'why', 'what'] for word in words),
            any(word in ['architecture', 'concept', 'theory', 'approach', 'method'] for word in words),
            ' and ' in query.lower() or ' or ' in query.lower(),  # Conjunctions
        ]
        
        return sum(semantic_indicators) >= 2
    
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
    
    def search_youtube_api(
        self,
        query: str,
        max_results: Optional[int] = None,
        fetch_transcripts: bool = True,
        store_transcripts: bool = True,
        published_after: Optional[datetime] = None,
        channel_id: Optional[str] = None,
        use_optimization: bool = True
    ) -> Dict[str, Any]:
        """
        Search YouTube using the Data API v3
        
        Args:
            query: Search query
            max_results: Number of results (max 50)
            fetch_transcripts: Whether to fetch transcripts
            store_transcripts: Whether to store in database
            published_after: Filter by publish date
            channel_id: Search within specific channel
            use_optimization: Whether to optimize query first
            
        Returns:
            Search results with metadata and optional transcripts
        """
        if not self.youtube_api:
            return {
                "error": "YouTube API not configured",
                "results": [],
                "total_found": 0,
                "quota_used": 0
            }
        
        # Optimize query if requested
        original_query = query
        if use_optimization:
            optimization = self.query_optimizer.optimize_query(query)
            query = optimization['optimized']
        
        try:
            # Search YouTube
            results = self.youtube_api.search_with_transcripts(
                query=query,
                max_results=max_results,
                fetch_transcripts=fetch_transcripts,
                store_in_db=store_transcripts,
                published_after=published_after,
                channel_id=channel_id
            )
            
            # Get quota status
            quota_status = self.youtube_api.get_quota_status()
            
            return {
                "original_query": original_query,
                "optimized_query": query if use_optimization else original_query,
                "results": results,
                "total_found": len(results),
                "source": "youtube_api",
                "quota_status": quota_status,
                "transcripts_fetched": fetch_transcripts,
                "transcripts_stored": store_transcripts
            }
            
        except QuotaExceededException as e:
            return {
                "error": "YouTube API quota exceeded",
                "error_details": str(e),
                "results": [],
                "total_found": 0,
                "quota_status": self.youtube_api.get_quota_status()
            }
        except Exception as e:
            return {
                "error": "YouTube API error",
                "error_details": str(e),
                "results": [],
                "total_found": 0
            }


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