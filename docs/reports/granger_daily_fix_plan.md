# Granger Daily Fix Plan - YouTube Transcripts

**Date**: 2025-01-06  
**Status**: CRITICAL - Multiple Systems Down  
**Priority**: URGENT  

## 🚨 Critical Issues Summary

1. **Test Suite**: 17/17 tests failing due to import errors
2. **MCP Server**: Cannot start - URI template error
3. **Code Compliance**: 3 files exceed 500-line limit
4. **Integration**: YouTube API imports broken

## 🔧 Immediate Actions (Fix Today)

### 1. Fix Test Import Paths (30 mins)
All tests are using `from src.youtube_transcripts` but should use `from youtube_transcripts`.

**Files to fix**:
- `tests/test_unified_search.py`
- `tests/test_search_widening.py`
- `tests/core/test_database.py`
- `tests/core/test_youtube.py`
- `tests/core/utils/test_scientific_extractors.py`
- `tests/agents/test_agents.py`
- `tests/integration/test_database_adapter.py`
- `tests/integration/test_arangodb_features.py`
- `tests/integration/test_arxiv_youtube_integration.py`
- `tests/mcp/test_prompts.py` (if exists)

**Fix pattern**:
```python
# WRONG
from src.youtube_transcripts.module import Thing

# CORRECT
from youtube_transcripts.module import Thing
```

### 2. Fix MCP Server (45 mins)

**Issue**: URI template error in FastMCP server
**Location**: `src/youtube_transcripts/mcp/server.py`

**Required fixes**:
1. Check URI template syntax in server.py
2. Ensure all prompts are properly registered
3. Fix the prompt registry initialization
4. Test with: `python -m youtube_transcripts.mcp.server`

### 3. Register MCP Prompts (30 mins)

**Current**: 0/10 prompts registered
**Expected**: 10 prompts including:
- youtube:capabilities
- youtube:find-transcripts
- youtube:research
- youtube:help
- youtube:quick-start
- youtube:find-code
- youtube:analyze-video
- youtube:view-code

**Fix in**: `src/youtube_transcripts/mcp/youtube_prompts.py`

### 4. Split Large Files (1 hour)

**Files to split**:
1. `tree_sitter_utils.py` (1099 lines) → Split into:
   - `tree_sitter_base.py`
   - `tree_sitter_extractors.py`
   - `tree_sitter_analyzers.py`

2. `unified_search.py` (996 lines) → Split into:
   - `unified_search_base.py`
   - `unified_search_handlers.py`
   - `unified_search_formatters.py`

3. `arango_integration.py` (616 lines) → Split into:
   - `arango_client.py`
   - `arango_operations.py`

### 5. Clean Up Imports (15 mins)

Run ruff to identify and fix:
```bash
cd /home/graham/workspace/experiments/youtube_transcripts
uv run ruff check src/ --fix
```

## 📋 Verification Checklist

After fixes, verify:

```bash
# 1. Test suite runs
uv run pytest -xvs

# 2. MCP server starts
python -m youtube_transcripts.mcp.server

# 3. Slash commands work
python -m youtube_transcripts.cli.app generate-claude

# 4. No files over 500 lines
find src -name "*.py" -exec wc -l {} + | sort -rn | head -20

# 5. Lint passes
uv run ruff check src/
```

## 🎯 Success Criteria

- [ ] All tests passing (or at least imports work)
- [ ] MCP server starts without errors
- [ ] 10/10 prompts registered and callable
- [ ] No Python files over 500 lines
- [ ] Ruff reports no import errors

## 📊 Expected Outcome

After these fixes:
- Test suite: 17/17 imports fixed (actual test results may vary)
- MCP compliance: 10/10 
- Code standards: 100% compliant
- Project status: FULLY OPERATIONAL

## 🚀 Next Steps

Once critical fixes are complete:
1. Run full test suite and fix any failing tests
2. Test all MCP prompts manually
3. Verify visual extraction pipeline
4. Create integration tests for new features
5. Update documentation

---

**Note**: This is a critical maintenance task. The project cannot function properly until these issues are resolved.