#!/usr/bin/env python3
"""
Test script to verify MCP prompts are properly registered
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from youtube_transcripts.mcp.youtube_prompts import register_all_prompts
from youtube_transcripts.mcp.prompts import get_prompt_registry


async def test_prompt_registration():
    """Test that all prompts are properly registered"""
    print("Testing MCP Prompt Registration...")
    
    # Register all prompts
    registry = register_all_prompts()
    
    # Expected prompts
    expected_prompts = [
        "youtube:capabilities",
        "youtube:find-transcripts",
        "youtube:research",
        "youtube:help",
        # Visual prompts (optional)
        "youtube:find-code",
        "youtube:analyze-video",
        "youtube:view-code"
    ]
    
    # Get registered prompts
    registered = registry.list_prompts()
    registered_names = [p.name for p in registered]
    
    print(f"\nRegistered prompts: {len(registered_names)}")
    for name in registered_names:
        print(f"  ✓ {name}")
    
    # Check core prompts
    core_prompts = expected_prompts[:4]
    missing_core = [p for p in core_prompts if p not in registered_names]
    
    if missing_core:
        print(f"\n❌ Missing core prompts: {missing_core}")
        return False
    else:
        print(f"\n✅ All {len(core_prompts)} core prompts registered")
    
    # Test executing a prompt
    print("\nTesting prompt execution...")
    try:
        result = await registry.execute("youtube:capabilities")
        if "YouTube Transcripts MCP Server Capabilities" in result:
            print("✅ Capabilities prompt executed successfully")
        else:
            print("❌ Capabilities prompt returned unexpected result")
            return False
    except Exception as e:
        print(f"❌ Error executing prompt: {e}")
        return False
    
    return True


async def test_mcp_server():
    """Test that MCP server can start"""
    print("\nTesting MCP server startup...")
    
    try:
        from youtube_transcripts.mcp.server import mcp, prompt_registry
        
        # Check server configuration
        print(f"Server name: {mcp.name}")
        print(f"Server description: {mcp.description}")
        
        # Check prompts are accessible from server
        if prompt_registry:
            prompts = prompt_registry.list_prompts()
            print(f"Prompts available to server: {len(prompts)}")
            return True
        else:
            print("❌ Prompt registry not initialized in server")
            return False
            
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False


async def main():
    """Run all tests"""
    print("=== MCP Prompts Verification ===\n")
    
    # Test prompt registration
    registration_ok = await test_prompt_registration()
    
    # Test server
    server_ok = await test_mcp_server()
    
    # Summary
    print("\n=== Summary ===")
    if registration_ok and server_ok:
        print("✅ All MCP prompt tests passed!")
        print("✅ MCP server is ready")
        print(f"\nTotal prompts registered: {len(get_prompt_registry().list_prompts())}")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)