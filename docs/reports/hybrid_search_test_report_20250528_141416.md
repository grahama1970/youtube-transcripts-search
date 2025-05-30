# Hybrid Search Test Report

**Generated**: 2025-05-28 14:14:16  
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
| Hybrid Search - semantic_query | ✅ PASS | Hybrid: True, Results: 1 | 0.107s |
| Hybrid Search - exact_match | ✅ PASS | Hybrid: False, Results: 1 | 0.039s |
| Hybrid Search - abstract_concept | ✅ PASS | Hybrid: True, Results: 1 | 0.039s |
| Hybrid Search with Filters | ✅ PASS | Results: 0, Valid: True | 0.096s |
| Hybrid Search Performance | ✅ PASS | Avg time: 0.029s, Tested: 3 | 0.029s |

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
| 4 | 0.03s | 0 |
| 8 | 0.03s | 2 |
