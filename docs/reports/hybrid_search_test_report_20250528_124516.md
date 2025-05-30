# Hybrid Search Test Report

**Generated**: 2025-05-28 12:45:16  
**Module**: GraphMemoryIntegration.search_with_arango_hybrid()

## Summary

- **Total Tests**: 5
- **Passed**: 4 ✅
- **Failed**: 1 ❌
- **Errors**: 0 🚫
- **Skipped**: 0 ⏭️
- **Success Rate**: 80.0%

## Test Results

| Test Name | Status | Key Metrics | Duration |
|-----------|--------|-------------|----------|
| Hybrid Search - semantic_query | ❌ FAIL | Hybrid: False, Results: 1 | 0.00s |
| Hybrid Search - exact_match | ✅ PASS | Hybrid: False, Results: 1 | 0.00s |
| Hybrid Search - abstract_concept | ✅ PASS | Hybrid: False, Results: 0 | 1.87s |
| Hybrid Search with Filters | ✅ PASS | Results: 0, Valid: True | 0.02s |
| Hybrid Search Performance | ✅ PASS | Avg time: 0.01s, Tested: 3 | 0.01s |

## Detailed Results

### Hybrid Search - semantic_query
**Query**: `understanding transformer architecture neural networks`
**Expected Fallback**: True
**Used Hybrid**: False

### Hybrid Search - exact_match
**Query**: `reinforcement learning PPO`
**Expected Fallback**: False
**Used Hybrid**: False

### Hybrid Search - abstract_concept
**Query**: `consciousness emergence artificial intelligence`
**Expected Fallback**: True
**Used Hybrid**: False

### Hybrid Search with Filters

### Hybrid Search Performance

#### Performance Details
| Query Words | Duration | Results |
|-------------|----------|----------|
| 1 | 0.02s | 0 |
| 4 | 0.00s | 2 |
| 8 | 0.00s | 1 |
