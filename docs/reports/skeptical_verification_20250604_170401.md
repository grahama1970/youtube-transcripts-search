# Skeptical Test Verification Report
Generated: 2025-06-04T17:04:01.855027
Confidence Threshold: 0.9
Max Verification Loops: 3

## Summary
- Total Test Suites: 14
- Passed: 0 ✅
- Failed: 13 ❌
- Uncertain: 1 ⚠️
- Average Confidence: 33.57%

## Detailed Results

| Test Suite | Status | Confidence | Loops | Issues |
|------------|--------|------------|-------|--------|
| tests/core/test_database.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/core/test_youtube.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/core/utils/test_scientific_extractors.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/integration/test_arangodb_features.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/integration/test_arxiv_youtube_integration.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/integration/test_database_adapter.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/mcp/test_prompts.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/agents/test_agents.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/level_0/test_youtube_transcripts_standardized.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/scenarios/test_level0_scenarios.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/test_search_widening.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/test_unified_search.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |
| tests/test_arangodb_connection.py | ⚠️ UNCERTAIN | 80.00% | 3 | LOW_CONFIDENCE |
| tests/test_integration_summary.py | ❌ FAIL | 30.00% | 2 | CONSISTENT_FAILURE |

## Issues Requiring Attention

- **tests/core/test_database.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/core/test_youtube.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/core/utils/test_scientific_extractors.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/integration/test_arangodb_features.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/integration/test_arxiv_youtube_integration.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/integration/test_database_adapter.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/mcp/test_prompts.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/agents/test_agents.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/level_0/test_youtube_transcripts_standardized.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/scenarios/test_level0_scenarios.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/test_search_widening.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/test_unified_search.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE
- **tests/test_arangodb_connection.py**: UNCERTAIN (Confidence: 80.00%)
  - LOW_CONFIDENCE
- **tests/test_integration_summary.py**: FAIL (Confidence: 30.00%)
  - CONSISTENT_FAILURE