# Relationship Extraction Test Report

**Generated**: 2025-05-28 14:17:03  
**Module**: GraphMemoryIntegration.extract_relationships_between_transcripts()

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
| Relationship Extraction - same_channel_pair | ✅ PASS | F1: 0.86, Found: 5 relationships | 0.001s |
| Relationship Extraction - different_channel_pair | ✅ PASS | F1: 0.67, Found: 3 relationships | 0.000s |
| Temporal Relationship - within_week | ✅ PASS | Temporal: True, Days: 4 | 0.000s |
| Temporal Relationship - over_week | ✅ PASS | Temporal: False, Days: None | 0.000s |
| Shared Entity Relationships | ✅ PASS | Match: 100%, Shared: 5 entities | 0.000s |

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
        "entity_name": "OpenAI",
        "entity_type": "organization",
        "confidence": 0.9
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
      "SAME_CHANNEL",
      "SHARES_ENTITY",
      "PUBLISHED_NEAR"
    ],
    "expected": [
      "SAME_CHANNEL",
      "SHARES_ENTITY",
      "SIMILAR_TOPIC",
      "PUBLISHED_NEAR"
    ],
    "matched": [
      "SAME_CHANNEL",
      "SHARES_ENTITY",
      "PUBLISHED_NEAR"
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
        "entity_name": "MCTS",
        "entity_type": "technical_term",
        "confidence": 0.6
      },
      {
        "entity_name": "AlphaGo",
        "entity_type": "technical_term",
        "confidence": 0.6
      },
      {
        "entity_name": "DeepMind",
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
      "SHARES_ENTITY",
      "SIMILAR_TOPIC"
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
      "openai",
      "microsoft",
      "gpt-4",
      "sam altman"
    ],
    "all": [
      "gpt-4",
      "microsoft",
      "openai",
      "gpt",
      "sam altman"
    ]
  }
}
```
