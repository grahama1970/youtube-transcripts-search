"""
YouTube Transcripts FastMCP Server
Module: server.py
Description: Functions for server operations

Implements an MCP server with prompts following the pattern from
"How I build Agentic MCP Servers for Claude Code (Prompts CHANGE Everything)"

External Dependencies:
- fastmcp: https://github.com/fastmcp/fastmcp
- youtube_transcripts: Local package

Example Usage:
>>> from youtube_transcripts.mcp.server import serve
>>> serve()
"""

import asyncio
from typing import Any

from fastmcp import FastMCP

# Import our core functionality
from ..core.database import get_transcript_by_video_id, initialize_database, search_transcripts
from ..core.transcript import process_channels
from ..mcp.prompts import get_prompt_registry
from ..mcp.youtube_prompts import register_all_prompts

# Initialize MCP server
mcp = FastMCP("youtube-transcripts")
mcp.description = "Intelligent YouTube transcript research and analysis"


# =============================================================================
# TOOLS - Individual actions
# =============================================================================

@mcp.tool()
async def fetch_transcript(video_id: str) -> dict[str, Any]:
    """Fetch a specific YouTube transcript by video ID"""
    try:
        transcript = get_transcript_by_video_id(video_id)
        if transcript:
            return {
                "success": True,
                "video_id": video_id,
                "title": transcript.get("title"),
                "channel": transcript.get("channel_name"),
                "content": transcript.get("content"),
                "duration": transcript.get("duration_seconds")
            }
        else:
            return {
                "success": False,
                "error": f"No transcript found for video ID: {video_id}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def search_youtube_transcripts(
    query: str,
    channels: list[str] | None = None,
    limit: int = 10
) -> dict[str, Any]:
    """Search through YouTube transcripts"""
    try:
        results = search_transcripts(query, channels, limit)
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def fetch_channel_transcripts(
    channel_urls: list[str],
    date_cutoff: str | None = None,
    cleanup_months: int | None = None
) -> dict[str, Any]:
    """Fetch transcripts from YouTube channels"""
    try:
        processed, deleted = process_channels(channel_urls, date_cutoff, cleanup_months)
        return {
            "success": True,
            "processed": processed,
            "deleted": deleted,
            "channels": channel_urls
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# PROMPTS - Workflows that compose tools
# =============================================================================

# Register all prompts from youtube_prompts.py
register_all_prompts()
prompt_registry = get_prompt_registry()


@mcp.prompt()
async def capabilities() -> str:
    """
    List all available MCP server capabilities including prompts, tools, and resources.
    This is the discovery prompt that helps users understand what they can do.
    """
    # Use the registered capabilities prompt
    return await prompt_registry.execute("youtube:capabilities")


@mcp.prompt()
async def find_transcripts(
    channel: str | None = None,
    date_range: str | None = None,
    limit: int = 10
) -> str:
    """
    Discover available YouTube transcripts with filtering options.
    Returns formatted list with quick actions.
    """
    return await prompt_registry.execute(
        "youtube:find-transcripts",
        channel=channel,
        date_range=date_range,
        limit=limit
    )


@mcp.prompt()
async def research(
    query: str,
    filters: dict[str, Any] | None = None,
    limit: int = 10
) -> str:
    """
    Research a topic across YouTube transcripts with guided workflow.
    Provides analysis and suggests next steps.
    """
    return await prompt_registry.execute(
        "youtube:research",
        query=query,
        filters=filters,
        limit=limit
    )


@mcp.prompt()
async def help(context: str | None = None) -> str:
    """
    Get context-aware help based on your current task.
    Provides specific guidance and examples.
    """
    return await prompt_registry.execute(
        "youtube:help",
        context=context
    )


@mcp.prompt()
async def quick_start() -> str:
    """
    Quick start guide for using YouTube Transcripts MCP server.
    Perfect for first-time users.
    """
    content = """# YouTube Transcripts Quick Start

Welcome! Here's how to get started:

## 1. Discover Available Content
```
/youtube find-transcripts
```

## 2. Research a Topic
```
/youtube research "your topic here"
```

## 3. Get Help Anytime
```
/youtube help
```

## Common Research Workflows

### Academic Research
1. `/youtube research "paper title or concept"`
2. Review results and note video IDs
3. `/youtube fetch-transcript <video_id>` for full transcript
4. Export findings for citation

### Technology Learning
1. `/youtube find-transcripts --channel "tech channel name"`
2. `/youtube research "specific technology"`
3. Follow suggested next steps

### Content Analysis
1. `/youtube capabilities` to see all features
2. Use tools directly for specific needs
3. Combine multiple searches for comprehensive analysis

## Pro Tips
- Use quotes for exact phrases: `"machine learning"`
- Filter by channel for focused results
- Check `/youtube help <task>` for specific guidance

Ready to start? Try `/youtube find-transcripts` to explore!
"""

    return content


# =============================================================================
# RESOURCES - Data access (if needed)
# =============================================================================

# Simple resource without template parameters - removed for now
# FastMCP requires template parameters in resources, which we don't need here


# =============================================================================
# Server initialization
# =============================================================================

def serve(host: str = "localhost", port: int = 5173):
    """Start the FastMCP server"""
    # Initialize database
    initialize_database()

    # Start server
    mcp.run(
        transport="stdio"  # Use stdio for Claude Code integration
    )


# =============================================================================
# Validation
# =============================================================================

if __name__ == "__main__":
    import asyncio

    # Test that prompts are properly registered
    async def validate():
        # Test capabilities
        result = await capabilities()
        assert "YouTube Transcripts MCP Server Capabilities" in result
        print("✅ Capabilities prompt works")

        # Test help
        help_result = await help()
        assert "Common Tasks" in help_result
        print("✅ Help prompt works")

        # Test quick start
        qs_result = await quick_start()
        assert "Quick Start" in qs_result
        print("✅ Quick start prompt works")

        print("\n✅ MCP server validation passed")
        print('✅ Server validation passed')

    # Run validation
    asyncio.run(validate())

    # Start server
    print("\nStarting MCP server...")
    serve()
