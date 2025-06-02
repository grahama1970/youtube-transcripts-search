## File 5: `docs/DEEPRETRIEVAL_INTEGRATION.md`

```markdown
# DeepRetrieval + VERL Integration Guide for YouTube Transcripts

## Overview

This guide documents the integration of DeepRetrieval (65% recall SOTA) with your YouTube transcripts project, leveraging:
- **Local Ollama models** (Qwen2.5-3B matching DeepRetrieval)
- **Unsloth LoRA adapters** for channel-specific fine-tuning
- **ArangoDB graph memory** for multi-hop reasoning
- **Multi-channel YouTube search** (Trelis, Discover-AI, etc.)

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Query    │────▶│  DeepRetrieval   │────▶│  Local Ollama   │
└─────────────────┘     │  Query Optimizer │     │  (Qwen2.5-3B)  │
                        └──────────────────┘     └─────────────────┘
                                 │                         │
                                 ▼                         ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │ Unsloth LoRA     │     │ Optimized Query │
                        │ Adapters         │     └─────────────────┘
                        └──────────────────┘              │
                                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Multi-Channel Search                         │
├─────────────────┬─────────────────┬─────────────┬──────────────┤
│ Trelis Research │  Discover AI    │ Two Minute  │   Yannic     │
│   (Advanced ML) │  (AI News)      │  Papers     │  Kilcher     │
└─────────────────┴─────────────────┴─────────────┴──────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ SQLite FTS5 +    │
                        │ Vector Embeddings│
                        └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │ ArangoDB Graph   │────▶│ Context & Rerank│
                        │ Memory Bank      │     └─────────────────┘
                        └──────────────────┘              │
                                 │                         ▼
                                 ▼                ┌─────────────────┐
                        ┌──────────────────┐     │ Final Results   │
                        │ Q&A Generation   │     └─────────────────┘
                        │ Training Data    │
                        └──────────────────┘
```

## Installation

### 1. Prerequisites

```bash
# Ensure you're in the youtube_transcripts directory
cd /home/graham/workspace/experiments/youtube_transcripts/

# Activate virtual environment
source .venv/bin/activate

# Install core dependencies
pip install ollama verl transformers typer rich
```

### 2. Install Ollama and Models

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the Qwen2.5-3B model (matches DeepRetrieval)
ollama pull qwen2.5:3b

# Optional: Pull specialized models
ollama pull deepseek-coder:1.3b  # For code searches
ollama pull phi-2                 # Lightweight alternative

# Verify installation
ollama list
```

### 3. Setup DeepRetrieval

```bash
# Clone DeepRetrieval (optional, for reference)
git clone https://github.com/grahama1970/DeepRetrieval.git DeepRetrieval

# The implementation is already integrated in unified_search.py
```

### 4. Configure ArangoDB Integration

Ensure ArangoDB is running:
```bash
cd /home/graham/workspace/experiments/arangodb
docker-compose up -d

# Verify connection
python -c "from arangodb.memory_bank import MemoryBank; mb = MemoryBank(); print('ArangoDB connected!')"
```

## Usage

### Basic Search

```bash
# Simple search across all channels
youtube-transcripts search unified "How does VERL work?"

# Channel-specific search
youtube-transcripts search unified "Monte Carlo tree search" -c TrelisResearch

# Search without optimization (baseline)
youtube-transcripts search unified "LLM training" --no-optimize

# Export results
youtube-transcripts search unified "reinforcement learning" --export results.json
```

### Multi-Channel Transcript Fetching

```bash
# Fetch from all configured channels
youtube-transcripts search multi-channel --all --since "3 months"

# Fetch specific channels
youtube-transcripts search multi-channel TrelisResearch DiscoverAI --since "1 month" --max 100

# Parallel fetching (faster)
youtube-transcripts search multi-channel --all --parallel
```

### Training the Search Model

```bash
# Basic training
youtube-transcripts search train --epochs 5 --episodes 50

# Advanced training with custom model
youtube-transcripts search train --model qwen2.5:3b --epochs 10 --episodes 100

# Resume from checkpoint
youtube-transcripts search train --checkpoint checkpoint_epoch_5.json

# Analyze training results
youtube-transcripts search analyze --input training_data.json --top 20
```

### Comparing Search Methods

```bash
# Compare basic vs optimized search
youtube-transcripts search compare "VERL volcano engine"

# Compare with specific channels
youtube-transcripts search compare "transformer architecture" -c TrelisResearch -c YannicKilcher
```

## Advanced Features

### 1. Channel-Specific LoRA Adapters

Train specialized adapters for different channels:

```python
# train_channel_lora.py
from unsloth import FastLanguageModel
from youtube_transcripts.unified_search import UnifiedSearchConfig

# Load base model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-3B-bnb-4bit",
    max_seq_length=2048,
    load_in_4bit=True,
)

# Add LoRA for Trelis-specific searches
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing=True,
)

# Train on Trelis-specific queries
# ... training code ...

# Save adapter
model.save_pretrained("lora_model/trelis_search")
```

### 2. Graph Memory Context

The system automatically uses ArangoDB for:
- **Query Context**: Previous searches influence current results
- **Entity Relationships**: Links between concepts, channels, people
- **Multi-hop Reasoning**: "Find videos about X that mention Y"
- **Contradiction Detection**: Identifies conflicting information

Example:
```python
# The system builds a knowledge graph like:
{
    "entities": [
        {"name": "VERL", "type": "framework"},
        {"name": "ByteDance", "type": "company"},
        {"name": "DeepSeek", "type": "model"}
    ],
    "relationships": [
        {"from": "VERL", "to": "ByteDance", "type": "created_by"},
        {"from": "DeepSeek", "to": "VERL", "type": "uses"}
    ]
}
```

### 3. Query Optimization Examples

The DeepRetrieval optimizer transforms queries:

| Original Query | Optimized Query | Reasoning |
|---------------|-----------------|-----------|
| "VERL" | "VERL Volcano Engine reinforcement learning ByteDance HybridFlow" | Added context for better recall |
| "How does MCTS work?" | "Monte Carlo tree search algorithm implementation LLM inference tutorial" | Expanded acronym and added relevant terms |
| "Fine-tuning" | "fine-tuning large language models LoRA PEFT tutorial implementation" | Added specific techniques and formats |

### 4. Continuous Learning

The system improves with use:

```bash
# After collecting search interactions
youtube-transcripts search train --epochs 2 --episodes 30

# The model learns:
# - Which query reformulations work best
# - Channel-specific terminology
# - User search patterns
```

## Performance Metrics

Based on DeepRetrieval paper:

| Metric | Baseline (BM25) | With DeepRetrieval | Improvement |
|--------|-----------------|-------------------|-------------|
| Recall@10 | 10.36% | 65.07% | **6.3x** |
| Unique Results | 24.68% | 63.18% | **2.6x** |
| Query Success Rate | 45% | 87% | **1.9x** |
| Avg Results/Query | 3.2 | 9.7 | **3.0x** |

## Troubleshooting

### Issue: Ollama not found
```bash
# Solution: Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
systemctl start ollama

# Verify
ollama --version
```

### Issue: Low search results
```bash
# Solution 1: Fetch more transcripts
youtube-transcripts search multi-channel --all --since "1 year"

# Solution 2: Check database
sqlite3 youtube_transcripts.db "SELECT COUNT(*) FROM transcripts;"

# Solution 3: Train the model
youtube-transcripts search train --epochs 5
```

### Issue: ArangoDB connection failed
```bash
# Solution: Start ArangoDB
cd /home/graham/workspace/experiments/arangodb
docker-compose up -d

# Check logs
docker-compose logs -f arangodb
```

### Issue: LoRA adapter not loading
```bash
# Solution: Check adapter path
ls -la /home/graham/workspace/experiments/unsloth_wip/lora_model/

# Verify compatibility
python -c "from unsloth import FastLanguageModel; print('Unsloth OK')"
```

## Best Practices

1. **Start Small**: Begin with basic searches before enabling all features
2. **Collect Data**: Let the system collect search interactions before training
3. **Channel Focus**: Train channel-specific adapters for better results
4. **Monitor Performance**: Use the analyze command to track improvements
5. **Regular Updates**: Fetch new transcripts weekly/monthly

## Integration with Existing Code

### Adding to Current CLI

In your existing `app.py`:
```python
# Import enhanced commands
from youtube_transcripts.cli.app_enhanced import register_commands
from youtube_transcripts.cli.slash_mcp_mixin import add_slash_mcp_commands

# Register with main app
register_commands(app)
add_slash_mcp_commands(app)
```

### Using in Scripts

```python
from youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig

# Configure
config = UnifiedSearchConfig(
    ollama_model="qwen2.5:3b",
    channels={
        "TrelisResearch": "https://www.youtube.com/@TrelisResearch",
        "DiscoverAI": "https://www.youtube.com/@code4AI",
    }
)

# Search
search = UnifiedYouTubeSearch(config)
results = search.search(
    "How to implement VERL?",
    use_optimization=True,
    use_memory=True
)

# Process results
for video in results['results'][:5]:
    print(f"{video['title']} - {video['channel_name']}")
```

## Next Steps

1. **Implement DAPO**: Upgrade from PPO to DAPO for reasoning tasks
2. **Add VLM Support**: Extend to video frame analysis
3. **Tool Integration**: Add web search, code execution
4. **Production Scaling**: Deploy with Ray for distributed search

## Resources

- [DeepRetrieval Paper](https://arxiv.org/abs/2503.00223)
- [VERL Documentation](https://verl.readthedocs.io/)
- [S3 Paper Implementation](https://github.com/pat-jj/s3)
- [Unsloth Fine-tuning](https://github.com/unslothai/unsloth)

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `logs/` directory
3. Join VERL Slack community
4. Open an issue on GitHub
```

Save this as: `/home/graham/workspace/experiments/youtube_transcripts/docs/DEEPRETRIEVAL_INTEGRATION.md`