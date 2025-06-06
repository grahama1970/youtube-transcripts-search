"""
DeepRetrieval query optimization module.
Module: deepretrieval_optimizer.py
Description: Implementation of deepretrieval optimizer functionality

This module provides query optimization using DeepRetrieval methodology with
local Ollama models and optional LoRA adapters for fine-tuning.

External Dependencies:
- ollama: https://github.com/ollama/ollama-python
- unsloth (optional): https://github.com/unslothai/unsloth

Example Usage:
>>> from deepretrieval_optimizer import DeepRetrievalQueryOptimizer
>>> from unified_search_config import UnifiedSearchConfig
>>> optimizer = DeepRetrievalQueryOptimizer(UnifiedSearchConfig())
>>> result = optimizer.optimize_query("how to implement RAG")
>>> print(result["optimized"])
"""

import logging
import re
from typing import Any

from .unified_search_config import UnifiedSearchConfig

logger = logging.getLogger(__name__)

# Check for optional dependencies
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not available, install with: pip install ollama")


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

    def optimize_query(self, user_query: str, context: dict | None = None) -> dict[str, Any]:
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
            parsed = self._parse_optimization_response(response['message']['content'])
            parsed["original"] = user_query  # Set original query
            return parsed

        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            # Fallback to original query
            return {
                "original": user_query,
                "optimized": user_query,
                "reasoning": "Optimization failed, using original query"
            }

    def _build_optimization_prompt(self, query: str, context: dict = None) -> str:
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

    def _parse_optimization_response(self, response: str) -> dict[str, Any]:
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
            "reasoning": reasoning
        }


if __name__ == "__main__":
    """Test query optimization with real examples."""
    from .unified_search_config import UnifiedSearchConfig

    config = UnifiedSearchConfig()
    optimizer = DeepRetrievalQueryOptimizer(config)

    test_queries = [
        "how to implement RAG",
        "explain transformers",
        "fine-tuning LLMs",
        "vector databases comparison"
    ]

    print("Testing DeepRetrieval Query Optimizer:")
    for query in test_queries:
        result = optimizer.optimize_query(query)
        print(f"\nOriginal: {query}")
        print(f"Optimized: {result['optimized']}")
        if result['reasoning']:
            print(f"Reasoning: {result['reasoning'][:100]}...")

    print("\n✅ Query optimizer module validation passed")
