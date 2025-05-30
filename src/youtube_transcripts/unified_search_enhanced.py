import ollama
import re
from typing import Dict, Any, List, Optional
import sys

# Import with error handling
try:
    from arangodb.core.search import SearchService, SearchConfig, SearchMethod
    from arangodb.core.memory.memory_agent import MemoryAgent
    from arangodb.core.arango_setup import connect_arango
    ARANGODB_AVAILABLE = True
except ImportError:
    ARANGODB_AVAILABLE = False
    print("Warning: ArangoDB not available, some features disabled")

class EnhancedDeepRetrievalOptimizer:
    def __init__(self, model: str = "qwen2.5:3b"):
        self.client = ollama.Client()
        self.model = model
        
        # Initialize ArangoDB if available
        if ARANGODB_AVAILABLE:
            try:
                self.arango_client = connect_arango()
                # The search service would need the database connection
                # For now, we'll skip this as the structure is different
                self.memory_agent = None  # Will need proper DB connection
                self.search_service = None
                self.search_config = None
                print("Note: ArangoDB modules loaded but search integration pending")
            except Exception as e:
                print(f"Warning: Could not initialize ArangoDB: {e}")
                self.memory_agent = None
                self.search_service = None
                self.search_config = None
        else:
            self.memory_agent = None
            self.search_service = None
            self.search_config = None
        
    def optimize_query(self, query: str) -> Dict[str, Any]:
        """Optimize query using DeepRetrieval approach"""
        context = self._get_query_context(query) if ARANGODB_AVAILABLE else "No context available"
        
        # Build smart query expansion based on known patterns
        expanded_terms = []
        
        # Always include original query
        expanded_terms.append(query)
        
        # Common acronym expansions
        acronym_map = {
            "VERL": "Volcano Engine Reinforcement Learning",
            "RL": "Reinforcement Learning",
            "ML": "Machine Learning", 
            "DL": "Deep Learning",
            "LLM": "Large Language Model",
            "NLP": "Natural Language Processing",
            "CV": "Computer Vision",
            "RLHF": "Reinforcement Learning from Human Feedback",
            "PPO": "Proximal Policy Optimization",
            "DPO": "Direct Preference Optimization"
        }
        
        # Check for acronyms in query
        query_upper = query.upper()
        for acronym, expansion in acronym_map.items():
            if acronym in query_upper:
                expanded_terms.append(expansion)
        
        # Add common related terms for short queries
        if len(query.split()) <= 3:
            expanded_terms.extend(["tutorial", "implementation", "framework", "example"])
        
        # Add AI/ML related terms if relevant
        ai_keywords = ["learning", "model", "neural", "train", "optimization", "algorithm"]
        if any(keyword in query.lower() for keyword in ai_keywords):
            expanded_terms.extend(["deep learning", "machine learning"])
        
        # Create optimized query
        optimized = " ".join(expanded_terms)
        
        # Use LLM for reasoning but with predetermined expansion
        prompt = f"""Explain why this query expansion will help find more relevant YouTube transcripts:

Original: "{query}"
Expanded: "{optimized}"

<think>
The expansion includes:
{chr(10).join(f"- {term}" for term in expanded_terms[1:])}
</think>
<answer>
{optimized}
</answer>"""
        
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7}
        )
        
        content = response['message']['content']
        
        # Parse response
        think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
        answer_match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
        
        # If LLM didn't parse correctly, use our pre-built optimized query
        if not answer_match or answer_match.group(1).strip() == query:
            optimized_query = optimized
        else:
            optimized_query = answer_match.group(1).strip()
        
        result = {
            "original": query,
            "optimized": optimized_query,
            "reasoning": think_match.group(1).strip() if think_match else f"Expanded query with: {', '.join(expanded_terms[1:])}",
            "context_used": bool(context != "No context available")
        }
        
        # Store optimization if ArangoDB available
        if ARANGODB_AVAILABLE:
            self._store_optimization(result)
        
        return result
    
    def _get_query_context(self, query: str) -> str:
        """Get relevant context from previous searches"""
        if not self.search_service:
            return "No previous context available"
            
        try:
            similar_searches = self.search_service.search(
                query=query,
                config=SearchConfig(
                    preferred_method=SearchMethod.SEMANTIC,
                    result_limit=5
                )
            )
            
            if similar_searches:
                return "\n".join([
                    f"- Previous: '{s.get('original', '')}' → '{s.get('optimized', '')}'"
                    for s in similar_searches[:3]
                ])
        except:
            pass
        return "No previous context available"
    
    def _store_optimization(self, result: Dict[str, Any]):
        """Store optimization in ArangoDB for future reference"""
        if not self.memory_agent:
            return
            
        try:
            # Would need proper implementation with memory_agent
            # For now, just skip storing
            pass
        except:
            pass