To improve the provided task list for clarity and methodical execution by a less sophisticated code executor, I'll optimize the structure, break down complex tasks into smaller, explicit steps, ensure unambiguous instructions, and maintain a logical sequence. The revised task list will include clear prerequisites, detailed steps, verification commands, and error-handling guidance, while preserving the original content's intent and technical details.

---

### `docs/tasks/001_deepretrieval_integration.md`

```markdown
# Task 001: DeepRetrieval Integration with Enhanced Architecture

**Component**: DeepRetrieval Query Optimizer with ArangoDB  
**Model**: qwen2.5:3b (targets 65% recall SOTA per DeepRetrieval paper)  
**Goal**: Set up local Ollama with Qwen2.5-3B, migrate transcript storage to ArangoDB, and enable unified hybrid search.

## Prerequisites
- **Hardware**: Machine with ≥8GB RAM, 20GB free disk space, and Docker installed.
- **Software**: Python 3.9+, pip, curl, git, Docker Compose.
- **Access**: Write permissions in `/home/graham/workspace/experiments/`.
- **Network**: Stable internet for downloading models and dependencies.
- **Files**: Ensure `/home/graham/workspace/experiments/youtube_transcripts/` exists with a basic project structure (e.g., `src/`, `pyproject.toml`).

## ✅ Task Checklist

### Phase 1: Core Setup
**Objective**: Install and verify Ollama with the Qwen2.5-3B model and test basic DeepRetrieval functionality.

- [ ] **Install Ollama**
  1. Run: `curl -fsSL https://ollama.ai/install.sh | sh`
  2. Start Ollama service: `sudo systemctl start ollama`
  3. Verify service: `sudo systemctl status ollama | grep Active`
     - Expected: `Active: active (running)`
     - If failed: Run `sudo systemctl restart ollama` and recheck.

- [ ] **Pull Required Models**
  1. Pull primary model: `ollama pull qwen2.5:3b`
  2. Pull code search model: `ollama pull deepseek-coder:1.3b`
  3. Pull lightweight model: `ollama pull phi-2`
  4. Verify models: `ollama list`
     - Expected: Lists `qwen2.5:3b`, `deepseek-coder:1.3b`, `phi-2`
     - If failed: Check disk space (`df -h`) and re-run pull commands.

- [ ] **Verify DeepRetrievalOptimizer Functionality**
  1. Navigate to project: `cd /home/graham/workspace/experiments/youtube_transcripts/`
  2. Run test script:
     ```bash
     python -c "
     from src.youtube_transcripts.unified_search import EnhancedDeepRetrievalOptimizer
     opt = EnhancedDeepRetrievalOptimizer()
     print('✅ Optimizer initialized')"
     ```
     - Expected: Prints `✅ Optimizer initialized`
     - If failed: Check Python path and ensure `unified_search.py` exists.

- [ ] **Test Query Optimization with Think/Answer Tags**
  1. Run test query:
     ```bash
     python -c "
     from src.youtube_transcripts.unified_search import EnhancedDeepRetrievalOptimizer
     opt = EnhancedDeepRetrievalOptimizer()
     result = opt.optimize_query('VERL training')
     print(f'Original: {result[\"original\"]}')
     print(f'Optimized: {result[\"optimized\"]}')"
     ```
     - Expected: Outputs original and optimized queries (e.g., `Original: VERL training`, `Optimized: ...`)
     - If failed: Verify Ollama service (`ollama ps`) and model availability.

### Phase 2: Database Migration
**Objective**: Migrate transcript storage from SQLite to ArangoDB and configure hybrid search.

- [ ] **Set Up ArangoDB**
  1. Navigate to: `cd /home/graham/workspace/experiments/arangodb`
  2. Start ArangoDB: `docker-compose up -d`
  3. Wait 30 seconds for startup.
  4. Verify connection:
     ```bash
     python -c "from arangodb.memory_bank import MemoryBank; mb = MemoryBank(); print('✅ ArangoDB connected')"
     ```
     - Expected: Prints `✅ ArangoDB connected`
     - If failed: Run `docker-compose logs` and check for errors; restart with `docker-compose down && docker-compose up -d`.

- [ ] **Migrate Transcripts from SQLite to ArangoDB**
  1. Ensure SQLite database exists at `youtube_transcripts.config.DB_PATH`.
  2. Run migration script:
     ```bash
     python /home/graham/workspace/experiments/youtube_transcripts/migrate_to_arangodb.py
     ```
     - Expected: Prints `✅ Migration complete: X transcripts`
     - If failed: Verify SQLite database path and ArangoDB connection.

- [ ] **Generate Embeddings for Transcripts**
  1. Use batch processing for efficiency:
     ```bash
     python -c "
     from youtube_transcripts.core.utils.embedding_utils import batch_generate_embeddings
     from arangodb.memory_bank import MemoryBank
     mb = MemoryBank()
     texts = [doc['title'] + ' ' + doc['transcript'][:500] for doc in mb.get_all('youtube_transcript')]
     embeddings = batch_generate_embeddings(texts)
     print(f'✅ Generated {len(embeddings)} embeddings')"
     ```
     - Expected: Prints number of embeddings generated.
     - If failed: Check memory usage (`free -m`) and reduce `batch_size` in `batch_generate_embeddings`.

- [ ] **Configure Hybrid Search**
  1. Update search configuration in `unified_search.py`:
     ```python
     self.search_config = SearchConfig(
         preferred_method=SearchMethod.HYBRID,
         bm25_weight=0.4,
         semantic_weight=0.6,
         enable_reranking=True,
         result_limit=20
     )
     ```
  2. Verify configuration:
     ```bash
     python -c "from src.youtube_transcripts.unified_search import EnhancedDeepRetrievalOptimizer; print(EnhancedDeepRetrievalOptimizer().search_config)"
     ```
     - Expected: Prints hybrid search configuration.
     - If failed: Check `SearchConfig` class in `arangodb.core.search`.

- [ ] **Test ArangoDB Advanced Search**
  1. Run search test:
     ```bash
     python -c "
     from arangodb.core.search import SearchService
     from arangodb.core.search import SearchConfig, SearchMethod
     search = SearchService()
     results = search.search('VERL training', config=SearchConfig(preferred_method=SearchMethod.HYBRID, result_limit=5))
     print(f'✅ Found {len(results)} results')"
     ```
     - Expected: Prints number of search results (>0).
     - If failed: Verify ArangoDB data and search configuration.

### Phase 3: Enhanced Integrations
**Objective**: Integrate arXiv MCP, GitHub extraction, and utility modules.

- [ ] **Add arXiv MCP Server to Configuration**
  1. Update `mcp_config.json`:
     ```bash
     python -c "
     import json
     with open('/home/graham/workspace/experiments/youtube_transcripts/mcp_config.json', 'r') as f:
         config = json.load(f)
     config['mcpServers']['arxiv'] = {
         'command': 'python',
         'args': ['-m', 'arxiv_mcp_server'],
         'cwd': '/home/graham/workspace/mcp-servers/arxiv-mcp-server'
     }
     with open('/home/graham/workspace/experiments/youtube_transcripts/mcp_config.json', 'w') as f:
         json.dump(config, f, indent=2)
     print('✅ Added arXiv MCP server')"
     ```
     - Expected: Prints `✅ Added arXiv MCP server`
     - If failed: Ensure `mcp_config.json` exists and is writable.

- [ ] **Test arXiv MCP Server**
  1. Navigate to: `cd /home/graham/workspace/mcp-servers/arxiv-mcp-server`
  2. Install dependencies: `pip install -e .`
  3. Test server: `python -m arxiv_mcp_server --test`
     - Expected: Returns exit code 0 and prints test success.
     - If failed: Check logs and dependencies.

- [ ] **Integrate GitHub Repository Extraction**
  1. Save `github_extractor.py` to `/home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/`.
  2. Test extraction:
     ```bash
     python -c "
     from youtube_transcripts.core.utils.github_extractor import extract_github_repos
     test_transcript = 'Check out github.com/volcengine/verl for the code'
     repos = extract_github_repos(test_transcript)
     print(f'✅ Found {len(repos)} repos: {repos[0][\"full_name\"]}')"
     ```
     - Expected: Prints `✅ Found 1 repos: volcengine/verl`
     - If failed: Verify `github_extractor.py` path and regex patterns.

- [ ] **Add Utility Files**
  1. Copy utility files:
     ```bash
     cp /home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/tree_sitter_utils.py \
        /home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/
     cp /home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/embedding_utils.py \
        /home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/
     ```
  2. Update `__init__.py`:
     ```bash
     echo "from .tree_sitter_utils import extract_code_metadata" >> \
          /home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/__init__.py
     echo "from .embedding_utils import get_embedding, cosine_similarity" >> \
          /home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/__init__.py
     ```
     - Expected: Files copied and `__init__.py` updated.
     - If failed: Verify source file paths and permissions.

- [ ] **Update Project Dependencies**
  1. Append to `pyproject.toml`:
     ```bash
     cat >> /home/graham/workspace/experiments/youtube_transcripts/pyproject.toml << 'EOF'
     [project]
     dependencies = [
         "ollama>=0.1.0",
         "claude-test-reporter @ git+https://github.com/grahama1970/claude-test-reporter.git",
         "claude-module-communicator @ git+https://github.com/grahama1970/claude-module-communicator.git",
     ]
     EOF
     ```
  2. Install dependencies: `cd /home/graham/workspace/experiments/youtube_transcripts/ && pip install -e .`
     - Expected: Dependencies installed without errors.
     - If failed: Check internet connection and git repository URLs.

### Phase 4: Validation
**Objective**: Validate the integration and ensure performance targets are met.

- [ ] **Run Comprehensive Search Tests**
  1. Run validation script:
     ```bash
     python /home/graham/workspace/experiments/youtube_transcripts/validation_test.py
     ```
     - Expected: Prints `✅ All validation tests passed!`
     - If failed: Review test output for specific failures and address (e.g., ArangoDB connection, embedding dimensions).

- [ ] **Verify 65% Recall Improvement**
  1. Run benchmark:
     ```bash
     python -c "
     from src.youtube_transcripts.unified_search import EnhancedDeepRetrievalOptimizer
     from arangodb.core.search import SearchService
     opt = EnhancedDeepRetrievalOptimizer()
     search = SearchService()
     result = opt.optimize_query('VERL training')
     results = search.search(result['optimized'], config=opt.search_config)
     print(f'✅ Recall test: {len(results)} results found')"
     ```
     - Expected: Returns sufficient results to indicate 65% recall improvement (compare with baseline SQLite search).
     - If failed: Adjust `bm25_weight` and `semantic_weight` in `SearchConfig`.

- [ ] **Generate Test Report**
  1. Run reporter:
     ```bash
     python -c "import claude_test_reporter; claude_test_reporter.generate_report('validation_test.py')"
     ```
     - Expected: Generates report file with test results.
     - If failed: Verify `claude-test-reporter` installation.

## Working Code Example
*Note*: Save as `unified_search.py` in `/home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/`.

```python
import ollama
import re
from typing import Dict, Any, List
from arangodb.core.search import SearchService, SearchConfig, SearchMethod
from arangodb.memory_bank import MemoryBank
from datetime import datetime
import sys

sys.path.extend([
    '/home/graham/workspace/experiments/arangodb',
    '/home/graham/workspace/experiments/youtube_transcripts'
])

class EnhancedDeepRetrievalOptimizer:
    def __init__(self, model: str = "qwen2.5:3b"):
        self.client = ollama.Client()
        self.model = model
        self.memory_bank = MemoryBank()
        self.search_service = SearchService()
        self.search_config = SearchConfig(
            preferred_method=SearchMethod.HYBRID,
            bm25_weight=0.4,
            semantic_weight=0.6,
            enable_reranking=True,
            result_limit=20
        )

    def optimize_query(self, query: str) -> Dict[str, Any]:
        context = self._get_query_context(query)
        prompt = f"""You are a search query optimizer for YouTube transcripts about AI/ML topics.
Given a user query, generate an optimized search query for maximum recall.

Previous search context:
{context}

User query: "{query}"

<think>
Consider:
1. Acronym expansion (e.g., VERL = Volcano Engine Reinforcement Learning)
2. Related terms (e.g., "training" → "training tutorial implementation")
3. Channel-specific terminology
4. Related technical concepts
</think>
<answer>
[Optimized query with expanded terms]
</answer>"""
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7}
        )
        content = response['message']['content']
        think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
        answer_match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
        result = {
            "original": query,
            "optimized": answer_match.group(1).strip() if answer_match else query,
            "reasoning": think_match.group(1).strip() if think_match else "",
            "context_used": bool(context)
        }
        self._store_optimization(result)
        return result

    def _get_query_context(self, query: str) -> str:
        try:
            similar_searches = self.search_service.search(
                query=query,
                config=SearchConfig(preferred_method=SearchMethod.SEMANTIC, result_limit=5)
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
        try:
            self.memory_bank.add({
                "type": "query_optimization",
                "original": result["original"],
                "optimized": result["optimized"],
                "reasoning": result["reasoning"],
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
```

## Database Migration Script
*Note*: Save as `migrate_to_arangodb.py` in `/home/graham/workspace/experiments/youtube_transcripts/`.

```python
import sqlite3
from pathlib import Path
from arangodb.memory_bank import MemoryBank
from youtube_transcripts.core.utils.embedding_utils import get_embedding
from youtube_transcripts.config import DB_PATH

def migrate_transcripts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT video_id, title, channel_name, publish_date, 
               transcript, summary, enhanced_transcript
        FROM transcripts
    """)
    memory_bank = MemoryBank()
    migrated = 0
    for row in cursor.fetchall():
        video_id, title, channel_name, publish_date, transcript, summary, enhanced = row
        embedding = get_embedding(f"{title} {transcript[:500]}")
        doc = {
            "video_id": video_id,
            "title": title,
            "channel_name": channel_name,
            "publish_date": publish_date,
            "transcript": transcript,
            "summary": summary,
            "enhanced_transcript": enhanced,
            "embedding": embedding,
            "type": "youtube_transcript"
        }
        memory_bank.add(doc)
        migrated += 1
        if migrated % 10 == 0:
            print(f"Migrated {migrated} transcripts...")
    conn.close()
    print(f"✅ Migration complete: {migrated} transcripts")

if __name__ == "__main__":
    migrate_transcripts()
```

## GitHub Repository Extraction
*Note*: Save as `github_extractor.py` in `/home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/core/utils/`.

```python
import re
from typing import List, Dict

def extract_github_repos(transcript: str) -> List[Dict[str, str]]:
    patterns = [
        r'github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)',
        r'(?:the\s+)?code\s+(?:at|on)\s+github[:\s]+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)',
        r'check\s+out\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)\s+on\s+github',
        r'github\s+repository[:\s]+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)',
        r'(?:my|our|the)\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)\s+(?:repo|repository)',
    ]
    repos = set()
    for pattern in patterns:
        matches = re.findall(pattern, transcript, re.IGNORECASE)
        repos.update(matches)
    results = []
    for repo in repos:
        if '/' in repo and len(repo.split('/')) == 2:
            user, name = repo.split('/')
            results.append({
                "full_name": repo,
                "user": user,
                "name": name,
                "url": f"https://github.com/{repo}"
            })
    return results
```

## Common Issues & Solutions

### Issue 1: ArangoDB Connection Failed
- **Solution**:
  ```bash
  cd /home/graham/workspace/experiments/arangodb
  docker-compose down
  docker-compose up -d
  sleep 30
  python -m arangodb.tests.test_connection
  ```
  - Check logs: `docker-compose logs`
  - Ensure Docker is running: `sudo systemctl start docker`

### Issue 2: Slow Embedding Generation
- **Solution**: Adjust `batch_size` in `batch_generate_embeddings`:
  ```python
  def batch_generate_embeddings(texts: List[str], batch_size: int = 5):  # Reduced batch size
      embeddings = []
      for i in range(0, len(texts), batch_size):
          batch = texts[i:i+batch_size]
          batch_embeddings = [get_embedding(text) for text in batch]
          embeddings.extend(batch_embeddings)
          print(f"Processed {i+len(batch)}/{len(texts)} embeddings...")
      return embeddings
  ```

### Issue 3: arXiv MCP Not Found
- **Solution**:
  ```bash
  cd /home/graham/workspace/mcp-servers/arxiv-mcp-server
  pip install -e .
  python -m arxiv_mcp_server --test
  ```
  - Verify `arxiv_mcp_server` module exists and dependencies are installed.

## Performance Metrics Target
- Query optimization: < 2 seconds
- Search latency: < 500ms
- Recall improvement: ≥65%
- Memory usage: ~4GB
- Concurrent searches: ≥10

## Next Steps
1. Complete all checklist items.
2. Run validation suite: `python validation_test.py`
3. Generate report: `python -c "import claude_test_reporter; claude_test_reporter.generate_report('validation_test.py')"`
4. Document performance metrics in `docs/performance_metrics.md`.
5. Proceed to Task 002: Training channel-specific LoRA adapters.
```

---

### Improvements Made
1. **Added Prerequisites Section**: Explicitly lists hardware, software, access, and file requirements to ensure the executor has all necessary conditions met.
2. **Granular Task Breakdown**: Split complex tasks (e.g., "Install Ollama and pull models") into smaller, numbered steps with clear commands and expected outputs.
3. **Verification Steps**: Added explicit verification commands (e.g., `ollama list`, `sudo systemctl status ollama`) for each task to confirm success or diagnose failures.
4. **Error Handling**: Included specific failure conditions and troubleshooting steps in each task (e.g., check disk space, restart services).
5. **Consistent Structure**: Each phase and task follows a uniform format: objective, numbered steps, expected output, and failure resolution.
6. **Simplified Commands**: Replaced multi-line scripts with single-line commands where possible (e.g., `ollama pull` commands) for clarity.
7. **Preserved Technical Details**: Kept all original code, configurations, and metrics intact, ensuring no loss of functionality.
8. **Clear File Paths**: Specified exact save locations for scripts (e.g., `unified_search.py`, `github_extractor.py`) to avoid ambiguity.
9. **Improved Readability**: Used consistent formatting (e.g., code blocks, bullet points) and avoided jargon unless necessary.
10. **Streamlined Validation**: Consolidated test commands and added clear expected outputs to reduce executor confusion.

This revised task list is designed to be executed methodically by a less sophisticated code executor, with clear instructions, minimal assumptions, and robust error handling.