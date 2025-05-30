# Entity Extraction Test Report

**Generated**: 2025-05-28 13:55:16  
**Module**: GraphMemoryIntegration.extract_entities_from_transcript()

## Summary

- **Total Tests**: 2
- **Passed**: 2 ✅
- **Failed**: 0 ❌
- **Errors**: 0 🚫
- **Skipped**: 0 ⏭️
- **Success Rate**: 100.0%

## Test Results

| Test Name | Status | Key Metrics | Duration |
|-----------|--------|-------------|----------|
| Entity Extraction - test_1 | ✅ PASS | Accuracy: 87.5%, Found: 7/8 | 0.00s |
| Entity Extraction - test_2 | ✅ PASS | Accuracy: 100.0%, Found: 8/8 | 0.00s |

## Detailed Results

### Entity Extraction - test_1
```json
{
  "people": {
    "found": [
      "John Smith"
    ],
    "missed": []
  },
  "organizations": {
    "found": [
      "Stanford University",
      "OpenAI",
      "Microsoft Research"
    ],
    "missed": []
  },
  "technical_terms": {
    "found": [
      "PPO",
      "VERL"
    ],
    "missed": [
      "LLMs"
    ]
  },
  "channels": {
    "found": [
      "TrelisResearch"
    ],
    "missed": []
  }
}
```

### Entity Extraction - test_2
```json
{
  "people": {
    "found": [
      "Jane Doe"
    ],
    "missed": []
  },
  "organizations": {
    "found": [
      "MIT",
      "Facebook AI Research",
      "Google DeepMind"
    ],
    "missed": []
  },
  "technical_terms": {
    "found": [
      "MCTS",
      "AlphaGo",
      "CNN"
    ],
    "missed": []
  },
  "channels": {
    "found": [
      "DiscoverAI"
    ],
    "missed": []
  }
}
```
