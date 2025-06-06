import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from youtube_transcripts.integrations.youtube_transcripts_module import YoutubeTranscriptsModule

async def run_tests():
    results = {
        "tests": [],
        "summary": {"total": 0, "passed": 0, "failed": 0}
    }
    
    module = YoutubeTranscriptsModule()
    await module.start()
    
    # Test 1: Module attributes
    test1 = {
        "nodeid": "test_module_attributes",
        "outcome": "passed"
    }
    try:
        assert module.name == "youtube_transcripts"
        assert hasattr(module, "version")
        assert len(module.capabilities) == 5
        print("✓ Test 1: Module attributes - PASSED")
    except Exception as e:
        test1["outcome"] = "failed"
        test1["call"] = {"longrepr": str(e)}
        print(f"✗ Test 1: Module attributes - FAILED: {e}")
    results["tests"].append(test1)
    
    # Test 2: Standardized response format
    test2 = {
        "nodeid": "test_standardized_response_format",
        "outcome": "passed"
    }
    try:
        response = await module.process({
            "action": "fetch_transcript",
            "data": {"video_id": "test123"}
        })
        assert response["success"] is True
        assert "data" in response
        assert isinstance(response["data"], dict)
        assert response["data"]["video_id"] == "test123"
        print("✓ Test 2: Standardized response format - PASSED")
    except Exception as e:
        test2["outcome"] = "failed"
        test2["call"] = {"longrepr": str(e)}
        print(f"✗ Test 2: Standardized response format - FAILED: {e}")
    results["tests"].append(test2)
    
    # Test 3: Error response format
    test3 = {
        "nodeid": "test_error_response_format",
        "outcome": "passed"
    }
    try:
        response = await module.process({
            "action": "unknown_action",
            "data": {}
        })
        assert response["success"] is False
        assert "error" in response
        assert "data" not in response
        print("✓ Test 3: Error response format - PASSED")
    except Exception as e:
        test3["outcome"] = "failed"
        test3["call"] = {"longrepr": str(e)}
        print(f"✗ Test 3: Error response format - FAILED: {e}")
    results["tests"].append(test3)
    
    await module.stop()
    
    # Update summary
    for test in results["tests"]:
        results["summary"]["total"] += 1
        if test["outcome"] == "passed":
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
    
    # Save results
    os.makedirs("test_reports", exist_ok=True)
    with open("test_reports/youtube_manual_test.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSummary: {results['summary']['passed']}/{results['summary']['total']} tests passed")
    
    return results["summary"]["failed"] == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
