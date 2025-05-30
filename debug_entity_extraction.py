#!/usr/bin/env python3
"""Debug script to test entity extraction with deduplication test text."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from youtube_transcripts.agents.graph_memory_integration import GraphMemoryIntegration

def main():
    # Exact test text from the deduplication test
    test_text = """
    OpenAI released GPT-4 in 2023. Microsoft partnered with OpenAI to integrate
    GPT-4 into their products. The GPT-4 model represents a significant advancement
    in AI technology. Microsoft's investment in OpenAI has been substantial.
    OpenAI continues to develop new AI models beyond GPT-4.
    """
    
    print("Test text:")
    print("-" * 80)
    print(test_text)
    print("-" * 80)
    print()
    
    # Initialize graph memory
    integration = GraphMemoryIntegration()
    
    # Extract entities
    print("Extracting entities...")
    entities = integration.extract_entities(test_text)
    
    # Print results
    print(f"\nTotal entities found: {len(entities)}")
    print("\nEntities by type:")
    
    # Group by type
    by_type = {}
    for entity in entities:
        entity_type = entity.get('type', 'Unknown')
        if entity_type not in by_type:
            by_type[entity_type] = []
        by_type[entity_type].append(entity)
    
    # Print grouped entities
    for entity_type, type_entities in sorted(by_type.items()):
        print(f"\n{entity_type} ({len(type_entities)}):")
        for entity in type_entities:
            print(f"  - {entity.get('name', 'N/A')}")
    
    # Check for specific entities
    print("\nChecking for expected entities:")
    entity_names = [entity.get('name', '').lower() for entity in entities]
    
    expected = ['openai', 'gpt-4', 'microsoft']
    for name in expected:
        found = any(name in entity_name for entity_name in entity_names)
        print(f"  - {name}: {'FOUND' if found else 'NOT FOUND'}")
    
    # Print raw entities for debugging
    print("\nRaw entity data:")
    for i, entity in enumerate(entities):
        print(f"\nEntity {i + 1}:")
        for key, value in entity.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main()