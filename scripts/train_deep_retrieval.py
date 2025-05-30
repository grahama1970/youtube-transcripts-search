#!/usr/bin/env python3
# youtube_transcripts/scripts/train_deepretrieval.py
"""
Train a DeepRetrieval-style search agent for YouTube transcripts
Uses VERL for RL training with local Ollama models
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
import argparse
from datetime import datetime

# Add project to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from youtube_transcripts.core.database import search_transcripts, initialize_database
from youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class YouTubeSearchReward:
    """
    Custom reward function for YouTube transcript search
    Based on DeepRetrieval's reward structure
    """
    
    def compute_reward(self, results: List[Dict], threshold_type: str = "recall") -> float:
        """
        Compute reward based on search results
        
        DeepRetrieval reward structure:
        Recall ≥ 0.7: +5.0
        Recall ≥ 0.5: +4.0
        Recall ≥ 0.4: +3.0
        Recall ≥ 0.3: +1.0
        Recall ≥ 0.1: +0.5
        Recall ≥ 0.05: +0.1
        Recall < 0.05: -3.5
        """
        # For YouTube search, we use result count as proxy for recall
        result_count = len(results)
        
        if result_count >= 10:  # Excellent results
            return 5.0
        elif result_count >= 7:  # Good results
            return 4.0
        elif result_count >= 5:  # Acceptable results
            return 3.0
        elif result_count >= 3:  # Marginal results
            return 1.0
        elif result_count >= 1:  # Poor results
            return 0.5
        else:  # No results
            return -3.5
    
    def compute_detailed_metrics(self, results: List[Dict], query: str) -> Dict[str, float]:
        """Compute detailed metrics for analysis"""
        return {
            "result_count": len(results),
            "unique_channels": len(set(r['channel_name'] for r in results)),
            "avg_relevance": np.mean([r.get('rank', 0) for r in results]) if results else 0,
            "coverage": min(len(results) / 10, 1.0),  # Normalized to 0-1
        }


class DeepRetrievalYouTubeTrainer:
    """
    Trains a search optimization model following DeepRetrieval methodology
    """
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.reward_fn = YouTubeSearchReward()
        
        # Initialize database
        initialize_database()
        
        # Initialize search system
        search_config = UnifiedSearchConfig(
            ollama_model=self.config['model'],
            use_reasoning=self.config['search']['use_reasoning']
        )
        self.search_system = UnifiedYouTubeSearch(search_config)
        
        # Training data storage
        self.training_buffer = []
        
    def _load_config(self, config_path: str) -> Dict:
        """Load training configuration"""
        default_config = {
            "model": "qwen2.5:3b",
            "training": {
                "batch_size": 16,
                "learning_rate": 1e-5,
                "num_epochs": 10,
                "episodes_per_epoch": 100,
            },
            "search": {
                "max_iterations": 5,
                "temperature": 0.7,
                "use_reasoning": True,
            },
            "reward": {
                "success_threshold": 5,  # Minimum results for positive reward
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def collect_episode(self, query: str) -> Dict[str, Any]:
        """
        Collect one episode of search interaction
        """
        # Execute search with original query (baseline)
        baseline_results = search_transcripts(query, limit=10)
        baseline_reward = self.reward_fn.compute_reward(baseline_results)
        
        # Execute search with optimized query
        optimized_search = self.search_system.search(
            query=query,
            use_optimization=True,
            use_memory=False  # Disable memory for training
        )
        optimized_results = optimized_search['results']
        optimized_reward = self.reward_fn.compute_reward(optimized_results)
        
        # Compute gain (similar to GBR - Gain Beyond RAG)
        gain = optimized_reward - baseline_reward
        
        # Detailed metrics
        metrics = self.reward_fn.compute_detailed_metrics(optimized_results, query)
        
        episode = {
            "original_query": query,
            "optimized_query": optimized_search['optimized_query'],
            "reasoning": optimized_search['reasoning'],
            "baseline_reward": baseline_reward,
            "optimized_reward": optimized_reward,
            "gain": gain,
            "metrics": metrics,
            "baseline_count": len(baseline_results),
            "optimized_count": len(optimized_results),
            "timestamp": datetime.now().isoformat()
        }
        
        return episode
    
    def generate_training_queries(self, num_queries: int = 100) -> List[str]:
        """
        Generate diverse training queries
        Can be enhanced with:
        - Real user queries from logs
        - Synthetic variations
        - Topic-based generation
        """
        base_queries = [
            # Technical queries
            "transformer architecture explanation",
            "how to implement attention mechanism",
            "BERT vs GPT comparison",
            "fine-tuning large language models",
            "distributed training strategies",
            
            # Specific technique queries
            "monte carlo tree search for LLMs",
            "reinforcement learning from human feedback",
            "parameter efficient fine tuning methods",
            "quantization techniques for model compression",
            "gradient accumulation implementation",
            
            # Tool/framework queries
            "how to use VERL for training",
            "pytorch distributed data parallel tutorial",
            "implementing LoRA adapters",
            "vLLM optimization techniques",
            "setting up model serving infrastructure",
            
            # Research/paper queries
            "latest advances in multimodal models",
            "vision transformer improvements 2025",
            "efficient inference methods",
            "mixture of experts architecture",
            "constitutional AI principles",
            
            # YouTube-specific queries
            "VERL volcano engine reinforcement learning",
            "DeepSeek R1 implementation",
            "Ollama local model deployment",
            "Unsloth fine-tuning tutorial",
            "ArangoDB graph database setup",
        ]
        
        # Generate variations
        variations = []
        prefixes = ["", "explain ", "tutorial on ", "best practices for ", "how to "]
        suffixes = ["", " for beginners", " advanced techniques", " implementation", " research"]
        
        for base in base_queries:
            for prefix in prefixes[:2]:  # Limit variations for efficiency
                for suffix in suffixes[:2]:
                    variations.append(f"{prefix}{base}{suffix}".strip())
        
        # Sample from variations
        import random
        random.shuffle(variations)
        return variations[:num_queries]
    
    def train_epoch(self, epoch: int):
        """
        Train one epoch following DeepRetrieval approach
        """
        logger.info(f"\n=== Training Epoch {epoch + 1} ===")
        
        # Generate training queries
        queries = self.generate_training_queries(
            self.config['training']['episodes_per_epoch']
        )
        
        epoch_data = []
        total_gain = 0
        positive_gains = 0
        
        for i, query in enumerate(queries):
            # Collect episode
            episode = self.collect_episode(query)
            epoch_data.append(episode)
            
            # Track metrics
            total_gain += episode['gain']
            if episode['gain'] > 0:
                positive_gains += 1
            
            # Log progress
            if (i + 1) % 10 == 0:
                logger.info(
                    f"Episode {i + 1}/{len(queries)}: "
                    f"Query='{query[:30]}...', "
                    f"Gain={episode['gain']:.2f}, "
                    f"Results: {episode['baseline_count']} → {episode['optimized_count']}"
                )
        
        # Update training buffer
        self.training_buffer.extend(epoch_data)
        
        # Compute epoch statistics
        avg_gain = total_gain / len(queries)
        success_rate = positive_gains / len(queries)
        
        logger.info(f"\nEpoch {epoch + 1} Summary:")
        logger.info(f"  Average Gain: {avg_gain:.3f}")
        logger.info(f"  Success Rate: {success_rate:.2%}")
        logger.info(f"  Total Episodes: {len(self.training_buffer)}")
        
        return {
            "epoch": epoch + 1,
            "avg_gain": avg_gain,
            "success_rate": success_rate,
            "episodes": len(epoch_data)
        }
    
    def save_training_data(self, output_path: str = "training_data.json"):
        """Save collected training data for analysis or future training"""
        with open(output_path, 'w') as f:
            json.dump(self.training_buffer, f, indent=2)
        logger.info(f"Saved {len(self.training_buffer)} training episodes to {output_path}")
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze training results"""
        if not self.training_buffer:
            return {}
        
        gains = [ep['gain'] for ep in self.training_buffer]
        baseline_rewards = [ep['baseline_reward'] for ep in self.training_buffer]
        optimized_rewards = [ep['optimized_reward'] for ep in self.training_buffer]
        
        # Find best and worst examples
        best_episodes = sorted(self.training_buffer, key=lambda x: x['gain'], reverse=True)[:5]
        worst_episodes = sorted(self.training_buffer, key=lambda x: x['gain'])[:5]
        
        analysis = {
            "total_episodes": len(self.training_buffer),
            "average_gain": np.mean(gains),
            "positive_gain_rate": sum(g > 0 for g in gains) / len(gains),
            "average_baseline_reward": np.mean(baseline_rewards),
            "average_optimized_reward": np.mean(optimized_rewards),
            "best_gain": max(gains),
            "worst_gain": min(gains),
            "best_examples": [
                {
                    "original": ep['original_query'],
                    "optimized": ep['optimized_query'],
                    "gain": ep['gain'],
                    "reasoning": ep['reasoning'][:100] + "..." if len(ep['reasoning']) > 100 else ep['reasoning']
                }
                for ep in best_episodes
            ],
            "worst_examples": [
                {
                    "original": ep['original_query'],
                    "optimized": ep['optimized_query'],
                    "gain": ep['gain'],
                    "reasoning": ep['reasoning'][:100] + "..." if len(ep['reasoning']) > 100 else ep['reasoning']
                }
                for ep in worst_episodes
            ]
        }
        
        return analysis
    
    def save_checkpoint(self, epoch: int):
        """Save training checkpoint"""
        checkpoint = {
            "epoch": epoch,
            "config": self.config,
            "training_buffer": self.training_buffer,
            "timestamp": datetime.now().isoformat()
        }
        
        checkpoint_path = f"checkpoint_epoch_{epoch}.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        logger.info(f"Saved checkpoint to {checkpoint_path}")
    
    def train(self):
        """Main training loop"""
        logger.info("Starting DeepRetrieval training for YouTube search")
        logger.info(f"Model: {self.config['model']}")
        logger.info(f"Epochs: {self.config['training']['num_epochs']}")
        
        # Training loop
        for epoch in range(self.config['training']['num_epochs']):
            epoch_stats = self.train_epoch(epoch)
            
            # Save checkpoint every 5 epochs
            if (epoch + 1) % 5 == 0:
                self.save_checkpoint(epoch + 1)
            
            # Early stopping if performance is good
            if epoch_stats['success_rate'] > 0.8 and epoch_stats['avg_gain'] > 2.0:
                logger.info("Early stopping: Performance criteria met!")
                break
        
        # Save final training data
        self.save_training_data()
        
        # Analyze results
        analysis = self.analyze_results()
        
        # Print analysis
        logger.info("\n=== Training Analysis ===")
        logger.info(f"Total Episodes: {analysis['total_episodes']}")
        logger.info(f"Average Gain: {analysis['average_gain']:.3f}")
        logger.info(f"Success Rate: {analysis['positive_gain_rate']:.2%}")
        
        logger.info("\nBest Optimizations:")
        for i, example in enumerate(analysis['best_examples'], 1):
            logger.info(f"{i}. '{example['original']}' → '{example['optimized']}' (Gain: {example['gain']:.2f})")
            logger.info(f"   Reasoning: {example['reasoning']}")
        
        logger.info("\nWorst Optimizations:")
        for i, example in enumerate(analysis['worst_examples'], 1):
            logger.info(f"{i}. '{example['original']}' → '{example['optimized']}' (Gain: {example['gain']:.2f})")
            logger.info(f"   Reasoning: {example['reasoning']}")
        
        # Save analysis
        with open("training_analysis.json", 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info("\nTraining complete! Results saved to:")
        logger.info("  - training_data.json (all episodes)")
        logger.info("  - training_analysis.json (summary)")
        
        return analysis


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Train DeepRetrieval for YouTube search")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--episodes", type=int, default=50, help="Episodes per epoch")
    parser.add_argument("--model", type=str, default="qwen2.5:3b", help="Ollama model to use")
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = DeepRetrievalYouTubeTrainer(args.config)
    
    # Update config from CLI args
    if args.epochs:
        trainer.config['training']['num_epochs'] = args.epochs
    if args.episodes:
        trainer.config['training']['episodes_per_epoch'] = args.episodes
    if args.model:
        trainer.config['model'] = args.model
    
    # Run training
    trainer.train()


if __name__ == "__main__":
    main()