# Relationship Extraction Test Report

**Generated**: 2025-05-28 12:46:46  
**Module**: GraphMemoryIntegration.extract_relationships_between_transcripts()

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
| Relationship Extraction - same_channel_pair | ✅ PASS | F1: 0.86, Found: 4 relationships | 0.00s |
| Relationship Extraction - different_channel_pair | ✅ PASS | F1: 0.67, Found: 3 relationships | 0.00s |
| Temporal Relationship - within_week | ✅ PASS | Temporal: True, Days: 4 | 0.00s |
| Temporal Relationship - over_week | ✅ PASS | Temporal: False, Days: None | 0.00s |
| Shared Entity Relationships | ❌ FAIL | Match: 25%, Shared: 2 entities | 0.00s |

## Detailed Results

### Relationship Extraction - same_channel_pair
```json
{
  "relationships": {
    "SHARES_ENTITY": [
      {
        "entity_name": "TrelisResearch",
        "entity_type": "youtube_channel",
        "confidence": 1.0
      },
      {
        "entity_name": "PPO",
        "entity_type": "technical_term",
        "confidence": 0.6
      }
    ],
    "SAME_CHANNEL": [
      {
        "channel_name": "TrelisResearch"
      }
    ],
    "PUBLISHED_NEAR": [
      {
        "days_apart": 2,
        "relationship": "within_week"
      }
    ]
  },
  "types": {
    "found": [
      "SHARES_ENTITY",
      "PUBLISHED_NEAR",
      "SAME_CHANNEL"
    ],
    "expected": [
      "SIMILAR_TOPIC",
      "SAME_CHANNEL",
      "SHARES_ENTITY",
      "PUBLISHED_NEAR"
    ],
    "matched": [
      "SHARES_ENTITY",
      "PUBLISHED_NEAR",
      "SAME_CHANNEL"
    ]
  }
}
```

### Relationship Extraction - different_channel_pair
```json
{
  "relationships": {
    "SHARES_ENTITY": [
      {
        "entity_name": "DeepMind",
        "entity_type": "technical_term",
        "confidence": 0.6
      },
      {
        "entity_name": "AlphaGo",
        "entity_type": "technical_term",
        "confidence": 0.6
      },
      {
        "entity_name": "MCTS",
        "entity_type": "technical_term",
        "confidence": 0.6
      }
    ]
  },
  "types": {
    "found": [
      "SHARES_ENTITY"
    ],
    "expected": [
      "SIMILAR_TOPIC",
      "SHARES_ENTITY"
    ],
    "matched": [
      "SHARES_ENTITY"
    ]
  }
}
```

### Shared Entity Relationships
```json
{
  "shared_entities": {
    "found": [
      "sam altman"
    ],
    "all": [
      "gpt",
      "sam altman"
    ]
  }
}
```
