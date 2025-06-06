#!/usr/bin/env python3
"""
Module: verify_test_readiness.py
Description: Verify system is ready for Level 0-4 testing

External Dependencies:
- arango: https://python-arango.readthedocs.io/
- requests: https://docs.python-requests.org/

Sample Input:
>>> python verify_test_readiness.py

Expected Output:
>>> System readiness report with pass/fail for each requirement

Example Usage:
>>> ./verify_test_readiness.py
"""

import sys
import os
import time
import subprocess
from pathlib import Path
import json

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_requirement(name, check_func):
    """Check a requirement and report status."""
    try:
        start = time.time()
        result, message = check_func()
        duration = time.time() - start
        if result:
            print(f"✅ {name} (took {duration:.3f}s)")
            if message:
                print(f"   {message}")
            return True
        else:
            print(f"❌ {name}: {message}")
            return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False


def check_youtube_api():
    """Check YouTube API key is configured."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        return True, f"API key configured (length: {len(api_key)})"
    return False, "YOUTUBE_API_KEY not found in environment"


def check_python_imports():
    """Check all required imports work."""
    try:
        from youtube_transcripts.research_pipeline import process_research_video
        from youtube_transcripts.link_extractor import extract_links_from_text
        from scripts.download_transcript import get_video_info
        return True, "All imports successful"
    except ImportError as e:
        return False, f"Import error: {e}"


def check_arangodb():
    """Check ArangoDB connection."""
    try:
        from arango import ArangoClient
        
        client = ArangoClient(hosts='http://localhost:8529')
        sys_db = client.db('_system', username='root', password='openSesame')
        version = sys_db.version()
        
        # Check research database
        has_research = sys_db.has_database('research')
        
        return True, f"ArangoDB v{version} - Research DB: {'exists' if has_research else 'missing'}"
    except Exception as e:
        return False, str(e)


def check_youtube_access():
    """Check if we can access real YouTube videos."""
    try:
        from scripts.download_transcript import get_video_info
        
        # Test with Rick Astley - always available
        info = get_video_info('dQw4w9WgXcQ')
        if info and info[0]:  # Has title
            return True, f"Can access YouTube: '{info[0]}'"
        return False, "No data returned from YouTube"
    except Exception as e:
        return False, f"YouTube access error: {e}"


def check_no_mocks():
    """Check that tests don't use mocks."""
    try:
        # Run grep to find mocks
        result = subprocess.run(
            ["grep", "-r", "mock\\|Mock\\|@patch\\|MagicMock", "tests/", "--include=*.py"],
            capture_output=True,
            text=True
        )
        
        # Filter out honeypot tests
        if result.returncode == 0:
            lines = [l for l in result.stdout.split('\n') 
                    if l and 'test_honeypot' not in l]
            mock_count = len(lines)
            if mock_count > 0:
                return False, f"Found {mock_count} files with mocks"
            
        return True, "No mocks found in tests"
    except Exception as e:
        return False, f"Error checking for mocks: {e}"


def check_honeypot_tests():
    """Check honeypot tests exist."""
    honeypot_path = Path("tests/test_honeypot.py")
    if honeypot_path.exists():
        # Count honeypot tests
        with open(honeypot_path) as f:
            content = f.read()
            honeypot_count = content.count('@pytest.mark.honeypot')
        return True, f"Found {honeypot_count} honeypot tests"
    return False, "test_honeypot.py not found"


def check_redis():
    """Check Redis connection (optional)."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        return True, "Redis available"
    except Exception:
        return True, "Redis not required (optional)"


def check_chat_ui():
    """Check Chat UI availability."""
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            return True, "Chat UI healthy"
        return False, f"Chat UI returned status {response.status_code}"
    except Exception:
        return False, "Chat UI not running (needed for Level 4)"


def check_arxiv_mcp():
    """Check ArXiv MCP server."""
    arxiv_path = Path("/home/graham/workspace/mcp-servers/arxiv-mcp-server")
    if arxiv_path.exists():
        return True, "ArXiv MCP server found (may not be running)"
    return False, "ArXiv MCP server not found"


def check_gitget():
    """Check GitGet availability."""
    gitget_path = Path("/home/graham/workspace/experiments/gitget")
    if gitget_path.exists():
        # Check if it's in PATH
        which_result = subprocess.run(["which", "gitget"], capture_output=True)
        if which_result.returncode == 0:
            return True, "GitGet found and in PATH"
        return True, "GitGet found but not in PATH"
    return False, "GitGet module not found"


def main():
    """Run all readiness checks."""
    print("=" * 60)
    print("YouTube Research Pipeline Test Readiness Check")
    print("=" * 60)
    print()
    
    # Define all checks
    checks = [
        ("YouTube API Key", check_youtube_api),
        ("Python Imports", check_python_imports),
        ("ArangoDB Connection", check_arangodb),
        ("Real Video Access", check_youtube_access),
        ("No Mocks in Tests", check_no_mocks),
        ("Honeypot Tests", check_honeypot_tests),
        ("Redis (Optional)", check_redis),
        ("Chat UI (Level 4)", check_chat_ui),
        ("ArXiv MCP Server", check_arxiv_mcp),
        ("GitGet Module", check_gitget),
    ]
    
    # Run all checks
    results = {}
    for name, check_func in checks:
        results[name] = check_requirement(name, check_func)
    
    # Summary
    print()
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    # Determine readiness by level
    level_readiness = {}
    level_readiness[0] = results["Python Imports"] and results["Honeypot Tests"]
    level_readiness[1] = level_readiness[0] and results["YouTube API Key"] and results["Real Video Access"]
    level_readiness[2] = level_readiness[1] and results["ArangoDB Connection"]
    level_readiness[3] = level_readiness[2] and results["No Mocks in Tests"]
    level_readiness[4] = level_readiness[3] and results["Chat UI (Level 4)"]
    
    print(f"Overall: {passed}/{total} checks passed")
    print()
    print("Level Readiness:")
    for level in range(5):
        status = "✅ Ready" if level_readiness.get(level, False) else "❌ Not Ready"
        print(f"  Level {level}: {status}")
    
    # Recommendations
    print()
    print("Recommendations:")
    
    if not results["No Mocks in Tests"]:
        print("  1. Remove all mocks from tests (CRITICAL for Granger standards)")
    
    if not results["Chat UI (Level 4)"]:
        print("  2. Start Chat UI for Level 4 testing:")
        print("     cd /home/graham/workspace/experiments/chat && docker-compose up -d")
    
    if not results["Real Video Access"]:
        print("  3. Check YouTube API quota and API key validity")
    
    if not all([results["ArXiv MCP Server"], results["GitGet Module"]]):
        print("  4. Some integrations missing - tests will be limited")
    
    # Exit code based on minimum readiness (Level 0)
    if level_readiness[0]:
        print()
        print("✅ System ready for at least Level 0 testing!")
        sys.exit(0)
    else:
        print()
        print("❌ System not ready for testing!")
        sys.exit(1)


if __name__ == "__main__":
    main()