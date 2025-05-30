# Integration Test Report

**Generated**: 2025-05-28 12:30:48  
**Test Database**: /tmp/test_youtube_transcripts.db

## Summary

- **Total Tests**: 4
- **Passed**: 0 ✅
- **Failed**: 1 ❌
- **Skipped**: 3 ⏭️
- **Success Rate**: 0.0%

## Test Results

| Test Name | Description | Result | Status | Duration |
|-----------|-------------|--------|--------|----------|
| Entity Extraction | Extract entities from transcript | SKIPPED - ArangoDB not available | ⏭️ Skip | 0s |
| Relationship Extraction | Extract relationships between transcripts | SKIPPED - ArangoDB not available | ⏭️ Skip | 0s |
| Hybrid Search Fallback | Test ArangoDB fallback when SQLite returns no results | SKIPPED - ArangoDB not available | ⏭️ Skip | 0s |
| Unified Search Integration | Test complete unified search | ERROR: fts5: syntax error near "VERL" | ❌ Fail | 3.32s |

## Detailed Results
