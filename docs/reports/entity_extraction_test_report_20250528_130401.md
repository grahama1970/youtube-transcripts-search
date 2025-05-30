# Entity Extraction Test Report

**Generated**: 2025-05-28 13:04:01  
**Module**: GraphMemoryIntegration.extract_entities_from_transcript()

## Summary

- **Total Tests**: 4
- **Passed**: 4 ✅
- **Failed**: 0 ❌
- **Errors**: 0 🚫
- **Skipped**: 0 ⏭️
- **Success Rate**: 100.0%

## Test Results

| Test Name | Status | Key Metrics | Duration |
|-----------|--------|-------------|----------|
| Entity Extraction - test_1 | ✅ PASS | Accuracy: 87.5%, Found: 7/8 | 0.00s |
| Entity Extraction - test_2 | ✅ PASS | Accuracy: 100.0%, Found: 8/8 | 0.00s |
| Entity Deduplication | ✅ PASS | Unique: 6, No duplicates: True | 0.00s |
| Entity Confidence Scores | ✅ PASS | Total: 12, Valid confidence: True | 0.00s |

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
      "Microsoft Research",
      "OpenAI"
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
      "Facebook AI Research",
      "Google DeepMind",
      "MIT"
    ],
    "missed": []
  },
  "technical_terms": {
    "found": [
      "AlphaGo",
      "MCTS",
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

### Entity Confidence Scores
```json
{
  "youtube_channel": {
    "min": 1.0,
    "max": 1.0,
    "avg": 1.0
  },
  "person": {
    "min": 0.7,
    "max": 0.7,
    "avg": 0.7
  },
  "organization": {
    "min": 0.8,
    "max": 0.9,
    "avg": 0.8666666666666667
  },
  "technical_term": {
    "min": 0.6,
    "max": 0.6,
    "avg": 0.6
  },
  "topic": {
    "min": 0.9,
    "max": 0.9,
    "avg": 0.9
  }
}
```
