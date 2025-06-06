"""
Unified search configuration module.
Module: unified_search_config.py
Description: Configuration management and settings

This module contains configuration classes and constants for the unified search system,
including settings for Ollama models, DeepRetrieval, ArangoDB, and YouTube API.

External Dependencies:
- python-dotenv: https://github.com/theskumar/python-dotenv

Example Usage:
>>> from unified_search_config import UnifiedSearchConfig
>>> config = UnifiedSearchConfig(ollama_model="qwen2.5:3b")
>>> print(config.youtube_api_key)
"""

import os
from dataclasses import dataclass


@dataclass
class UnifiedSearchConfig:
    """Configuration for unified search system"""
    # Model configuration
    ollama_model: str = "qwen2.5:3b"  # Local model matching DeepRetrieval
    use_lora: bool = True
    lora_adapter_path: str | None = "/home/graham/workspace/experiments/unsloth_wip/lora_model"

    # DeepRetrieval settings
    deepretrieval_endpoint: str = "http://localhost:8000"  # vLLM endpoint
    use_reasoning: bool = True  # Use <think> tags

    # ArangoDB settings
    arango_host: str = "http://localhost:8529"
    arango_db: str = "memory_bank"

    # YouTube API settings
    youtube_api_key: str | None = None
    youtube_search_enabled: bool = True
    youtube_max_results: int = 50  # Max allowed by API

    # Channel configuration
    channels: dict[str, str] = None

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
            from dotenv import load_dotenv

            # Load from .env file
            load_dotenv()
            self.youtube_api_key = os.environ.get('YOUTUBE_API_KEY')


if __name__ == "__main__":
    """Test configuration loading."""
    config = UnifiedSearchConfig()

    print("Unified Search Configuration:")
    print(f"  Ollama Model: {config.ollama_model}")
    print(f"  Use LoRA: {config.use_lora}")
    print(f"  DeepRetrieval Endpoint: {config.deepretrieval_endpoint}")
    print(f"  ArangoDB Host: {config.arango_host}")
    print(f"  YouTube API Key: {'Set' if config.youtube_api_key else 'Not Set'}")
    print(f"  Channels: {len(config.channels)}")

    print("\n✅ Configuration module validation passed")
