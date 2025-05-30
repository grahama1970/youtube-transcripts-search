# Hybrid Search Test Report

**Generated**: 2025-05-28 13:12:40  
**Module**: GraphMemoryIntegration.search_with_arango_hybrid()

## Summary

- **Total Tests**: 5
- **Passed**: 5 ✅
- **Failed**: 0 ❌
- **Errors**: 0 🚫
- **Skipped**: 0 ⏭️
- **Success Rate**: 100.0%

## Test Results

| Test Name | Status | Key Metrics | Duration |
|-----------|--------|-------------|----------|
| Hybrid Search - semantic_query | ✅ PASS | Hybrid: True, Results: 1 | 0.10s |
| Hybrid Search - exact_match | ✅ PASS | Hybrid: False, Results: 1 | 0.04s |
| Hybrid Search - abstract_concept | ✅ PASS | Hybrid: True, Results: 1 | 0.04s |
| Hybrid Search with Filters | ✅ PASS | Results: 0, Valid: True | 0.10s |
| Hybrid Search Performance | ✅ PASS | Avg time: 0.03s, Tested: 3 | 0.03s |

## Detailed Results

### Hybrid Search - semantic_query
**Query**: `understanding transformer architecture neural networks`
**Expected Fallback**: True
**Used Hybrid**: True

### Hybrid Search - exact_match
**Query**: `reinforcement learning PPO`
**Expected Fallback**: False
**Used Hybrid**: False

### Hybrid Search - abstract_concept
**Query**: `consciousness emergence artificial intelligence`
**Expected Fallback**: True
**Used Hybrid**: True

### Hybrid Search with Filters

### Hybrid Search Performance

#### Performance Details
| Query Words | Duration | Results |
|-------------|----------|----------|
| 1 | 0.03s | 0 |
| 4 | 0.03s | 2 |
| 8 | 0.03s | 2 |
