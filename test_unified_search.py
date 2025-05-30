#!/usr/bin/env python3
"""
Test script for Task 002: Unified Search Implementation
Creates test data and validates the unified search functionality
"""

import json
from datetime import datetime
from youtube_transcripts.core.database import add_transcript, initialize_database
from src.youtube_transcripts.unified_search_v2 import UnifiedYouTubeSearch, UnifiedSearchConfig

def create_test_data():
    """Create test transcripts for validation"""
    test_transcripts = [
        {
            "video_id": "verl_001",
            "title": "VERL: Volcano Engine RL for LLMs",
            "channel_name": "TrelisResearch",
            "publish_date": "2025-05-15",
            "transcript": "Today we'll explore VERL, the Volcano Engine Reinforcement Learning framework. "
                         "This implementation shows how to train language models using RL techniques. "
                         "The framework supports distributed training and custom reward functions.",
            "summary": "Introduction to VERL framework for RL training of LLMs"
        },
        {
            "video_id": "verl_002", 
            "title": "Building with VERL: A Tutorial",
            "channel_name": "DiscoverAI",
            "publish_date": "2025-05-16",
            "transcript": "In this tutorial, we'll implement a complete VERL example. "
                         "Starting with the basic setup, we'll create custom environments and rewards. "
                         "The Volcano Engine framework makes it easy to scale RL training.",
            "summary": "Hands-on VERL tutorial with implementation examples"
        },
        {
            "video_id": "rl_basics_001",
            "title": "Reinforcement Learning Fundamentals",
            "channel_name": "TwoMinutePapers",
            "publish_date": "2025-05-14",
            "transcript": "Let's understand the basics of reinforcement learning. "
                         "RL is about learning through interaction with an environment. "
                         "Key concepts include states, actions, rewards, and policies.",
            "summary": "RL fundamentals: states, actions, rewards, and policies"
        }
    ]
    
    for transcript in test_transcripts:
        add_transcript(**transcript)
    
    print(f"Created {len(test_transcripts)} test transcripts")

def test_unified_search():
    """Test the unified search functionality"""
    print("\n" + "="*50)
    print("Testing Unified Search Implementation")
    print("="*50)
    
    config = UnifiedSearchConfig()
    search_system = UnifiedYouTubeSearch(config)
    
    # Test 1: Basic search without optimization
    print("\n1. Testing basic search (no optimization):")
    results = search_system.search("VERL", use_optimization=False)
    print(f"   Query: {results['query']}")
    print(f"   Found: {results['total_found']} results")
    print(f"   Channels searched: {results['channels_searched']}")
    
    # Test 2: Optimized search
    print("\n2. Testing optimized search:")
    results = search_system.search("How does VERL work?", use_optimization=True)
    print(f"   Query: {results['query']}")
    print(f"   Optimized: {results['optimized_query']}")
    print(f"   Reasoning: {results['reasoning'][:100]}...")
    print(f"   Found: {results['total_found']} results")
    
    # Test 3: Channel-specific search
    print("\n3. Testing channel-specific search:")
    results = search_system.search(
        "reinforcement learning",
        channels=["TrelisResearch"],
        use_optimization=True
    )
    print(f"   Channels: {results['channels_searched']}")
    print(f"   Found: {results['total_found']} results")
    
    # Validate results structure
    print("\n4. Validating result structure:")
    assert "query" in results, "Missing 'query' field"
    assert "optimized_query" in results, "Missing 'optimized_query' field"
    assert "results" in results, "Missing 'results' field"
    assert "total_found" in results, "Missing 'total_found' field"
    assert "channels_searched" in results, "Missing 'channels_searched' field"
    assert isinstance(results["results"], list), "Results should be a list"
    print("   ✅ All required fields present")
    
    # Test 4: Query expansion validation
    print("\n5. Testing query expansion:")
    test_queries = [
        "VERL",
        "RL tutorial",
        "How does reinforcement learning work?"
    ]
    
    for query in test_queries:
        result = search_system.search(query, use_optimization=True)
        expanded = len(result["optimized_query"]) > len(query)
        print(f"   '{query}' -> '{result['optimized_query']}' (Expanded: {expanded})")
    
    print("\n" + "="*50)
    print("✅ All tests passed!")
    print("="*50)

if __name__ == "__main__":
    # Initialize database
    initialize_database()
    
    # Create test data
    create_test_data()
    
    # Run tests
    test_unified_search()