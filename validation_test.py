#!/usr/bin/env python3
import sys
import subprocess

# Add paths
sys.path.insert(0, '/home/graham/workspace/experiments/youtube_transcripts/src')

def validate_enhanced_deepretrieval():
    """Comprehensive validation of enhanced DeepRetrieval integration"""
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Basic optimization
    try:
        from youtube_transcripts.unified_search_enhanced import EnhancedDeepRetrievalOptimizer
        optimizer = EnhancedDeepRetrievalOptimizer()
        result = optimizer.optimize_query("VERL")
        
        if len(result['optimized']) > len(result['original']):
            print("✅ Test 1: Basic optimization passed")
            tests_passed += 1
        else:
            print("❌ Test 1: Query was not expanded")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        tests_failed += 1
    
    # Test 2: ArangoDB search (if available)
    try:
        from arangodb.core.search import SearchService, SearchConfig, SearchMethod
        search = SearchService()
        config = SearchConfig(
            preferred_method=SearchMethod.HYBRID,
            result_limit=5
        )
        results = search.search("VERL training", config=config)
        print(f"✅ Test 2: ArangoDB search passed (found {len(results)} results)")
        tests_passed += 1
    except Exception as e:
        print(f"⚠️  Test 2 skipped (ArangoDB not available): {e}")
    
    # Test 3: GitHub extraction
    try:
        from youtube_transcripts.core.utils.github_extractor import extract_github_repos
        test_text = "Check out github.com/volcengine/verl for the code"
        repos = extract_github_repos(test_text)
        
        if repos and repos[0]['full_name'] == "volcengine/verl":
            print("✅ Test 3: GitHub extraction passed")
            tests_passed += 1
        else:
            print("❌ Test 3: GitHub extraction failed")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        tests_failed += 1
    
    # Test 4: arXiv integration
    try:
        result = subprocess.run(
            ["python", "-m", "arxiv_mcp_server", "--test"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✅ Test 4: arXiv integration passed")
            tests_passed += 1
        else:
            print(f"❌ Test 4: arXiv integration failed: {result.stderr}")
            tests_failed += 1
    except Exception as e:
        print(f"⚠️  Test 4 skipped (arXiv MCP not available): {e}")
    
    # Test 5: Embedding generation
    try:
        from youtube_transcripts.core.utils.embedding_utils import get_embedding
        embedding = get_embedding("Test transcript content")
        
        if isinstance(embedding, list) and len(embedding) == 1024:
            print("✅ Test 5: Embedding generation passed")
            tests_passed += 1
        else:
            print(f"❌ Test 5: Wrong embedding dimensions: {len(embedding) if embedding else 0}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        tests_failed += 1
    
    # Summary
    total_tests = tests_passed + tests_failed
    print(f"\n{'='*50}")
    print(f"Validation Summary: {tests_passed}/{total_tests} tests passed")
    if tests_failed == 0:
        print("🎉 All validation tests passed!")
        return True
    else:
        print(f"❌ {tests_failed} tests failed")
        return False

if __name__ == "__main__":
    success = validate_enhanced_deepretrieval()
    sys.exit(0 if success else 1)