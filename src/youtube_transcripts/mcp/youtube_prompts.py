"""
YouTube Transcripts MCP Prompts
Module: youtube_prompts.py
Description: Functions for youtube prompts operations

Implements high-level prompts that compose tools into guided workflows
for YouTube transcript research and analysis.

External Dependencies:
- youtube_transcripts: Local package

Example Usage:
>>> from youtube_transcripts.mcp.youtube_prompts import register_all_prompts
>>> register_all_prompts()
"""

import sqlite3
from typing import Any

from ..config import DB_PATH
from ..core.database import search_transcripts
from ..mcp.prompts import format_prompt_response, get_prompt_registry, mcp_prompt


@mcp_prompt(
    name="youtube:capabilities",
    description="List all available MCP server capabilities including prompts, tools, and resources",
    category="discovery",
    next_steps=[
        "Use /youtube:find-transcripts to discover available transcripts",
        "Use /youtube:research to start a research workflow",
        "Use /youtube:help for context-aware assistance"
    ]
)
async def list_capabilities(registry: Any = None) -> str:
    """List all available capabilities of the YouTube Transcripts MCP server"""

    # Get registry if not provided
    if registry is None:
        registry = get_prompt_registry()

    # Get all prompts by category
    categories = registry.get_categories()

    content = """# YouTube Transcripts MCP Server Capabilities

This MCP server provides intelligent access to YouTube transcript data with 
guided workflows for research, analysis, and knowledge extraction.

## Quick Start Workflow

1. **Discover Content**: Use `/youtube:find-transcripts` to explore available transcripts
2. **Research Topics**: Use `/youtube:research` to find content on specific topics  
3. **Analyze Content**: Use `/youtube:analyze` for deep analysis of transcripts
4. **Export Results**: Use `/youtube:export` to generate research reports

## Available Prompts
"""

    # Add prompts by category
    for category, prompt_names in categories.items():
        if prompt_names:
            content += f"\n### {category.title()} Prompts\n"
            for name in prompt_names:
                prompt = registry.get(name)
                if prompt:
                    content += f"- `/{name}` - {prompt.description}\n"

    # Add tool information
    content += """
## Core Tools

- `fetch_transcript` - Fetch a YouTube transcript by video ID
- `search_transcripts` - Search transcripts by keyword
- `analyze_transcript` - Analyze transcript content
- `list_transcripts` - List all available transcripts
- `export_results` - Export search/analysis results

## Key Features

- **Unified Search**: Intelligent search across titles, content, and metadata
- **Citation Detection**: Automatically extract paper citations from transcripts
- **Speaker Extraction**: Identify and track different speakers
- **Content Classification**: Categorize transcripts by topic and type
- **Scientific Metadata**: Extract research-relevant information
"""

    suggestions = {
        "/youtube:find-transcripts": "Discover available transcript data",
        "/youtube:research 'AI safety'": "Research a specific topic",
        "/youtube:help": "Get contextual help"
    }

    return format_prompt_response(
        content=content,
        suggestions=suggestions
    )


@mcp_prompt(
    name="youtube:find-transcripts",
    description="Discover available YouTube transcripts with filtering options",
    category="discovery",
    parameters={
        "channel": {"type": "string", "description": "Filter by channel name"},
        "date_range": {"type": "string", "description": "Date range (e.g., 'last_week', 'last_month')"},
        "limit": {"type": "integer", "description": "Maximum number of results"}
    },
    next_steps=[
        "Use /youtube:research to search within discovered transcripts",
        "Use /youtube:analyze on specific transcripts"
    ]
)
async def find_transcripts(
    channel: str | None = None,
    date_range: str | None = None,
    limit: int = 10
) -> str:
    """Discover available YouTube transcripts"""

    try:
        # Build query
        query = "SELECT * FROM transcripts"
        conditions = []
        params = []

        if channel:
            conditions.append("channel_name LIKE ?")
            params.append(f"%{channel}%")

        if date_range:
            # Simple date range handling
            if date_range == "last_week":
                conditions.append("datetime(fetched_at) > datetime('now', '-7 days')")
            elif date_range == "last_month":
                conditions.append("datetime(fetched_at) > datetime('now', '-30 days')")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY fetched_at DESC LIMIT {limit}"

        # Execute query
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        transcripts = cursor.fetchall()
        conn.close()

        if not transcripts:
            return format_prompt_response(
                content="No transcripts found matching your criteria.",
                suggestions={
                    "/youtube:find-transcripts": "Try without filters",
                    "/youtube:help": "Get help with searching"
                }
            )

        # Format results
        content = f"# Found {len(transcripts)} Transcripts\n\n"

        transcript_list = []
        for t in transcripts:
            video_id = t['video_id']
            title = t['title']
            channel = t['channel_name']
            duration = t['duration_seconds'] // 60 if t['duration_seconds'] else 'N/A'

            content += f"## {title}\n"
            content += f"- **Video ID**: {video_id}\n"
            content += f"- **Channel**: {channel}\n"
            content += f"- **Duration**: {duration} minutes\n"
            content += f"- **URL**: https://youtube.com/watch?v={video_id}\n\n"

            transcript_list.append({
                "video_id": video_id,
                "title": title,
                "channel": channel
            })

        suggestions = {
            f"/youtube:analyze '{transcript_list[0]['video_id']}'": f"Analyze '{transcript_list[0]['title'][:30]}...'",
            "/youtube:research": "Search across all transcripts"
        }

        return format_prompt_response(
            content=content,
            suggestions=suggestions,
            data={"transcripts": transcript_list}
        )

    except Exception as e:
        return format_prompt_response(
            content=f"Error discovering transcripts: {e!s}",
            suggestions={
                "/youtube:capabilities": "View all capabilities",
                "/youtube:help": "Get help"
            }
        )


@mcp_prompt(
    name="youtube:research",
    description="Research a topic across YouTube transcripts with guided workflow",
    category="research",
    parameters={
        "query": {"type": "string", "description": "Research query or topic"},
        "filters": {"type": "object", "description": "Optional filters (channel, date_range, etc.)"},
        "limit": {"type": "integer", "description": "Maximum results per search"}
    },
    examples=[
        "Research 'machine learning optimization techniques'",
        "Find discussions about 'AI safety' from specific channels"
    ],
    next_steps=[
        "Use /youtube:analyze for deep analysis of specific results",
        "Use /youtube:validate-claims to cross-reference findings",
        "Use /youtube:export to generate a research report"
    ]
)
async def research_topic(
    query: str,
    filters: dict[str, Any] | None = None,
    limit: int = 10
) -> str:
    """Research a topic across YouTube transcripts"""

    try:
        # Use the search_transcripts function from database module
        channel_list = None
        if filters and 'channels' in filters:
            channel_list = filters['channels']

        results = search_transcripts(
            query=query,
            channel_names=channel_list,
            limit=limit
        )

        if not results:
            return format_prompt_response(
                content=f"No results found for '{query}'.",
                suggestions={
                    "/youtube:find-transcripts": "Browse available transcripts",
                    f"/youtube:research '{query}' --limit 20": "Try with more results"
                }
            )

        # Format results
        content = f"# Research Results: '{query}'\n\n"
        content += f"Found {len(results)} relevant transcript segments.\n\n"

        for i, result in enumerate(results[:5], 1):  # Show top 5
            content += f"## {i}. {result['title']}\n"
            content += f"**Channel**: {result['channel_name']}\n"
            content += f"**Relevance**: {result['score']:.2f}\n"
            content += f"**Excerpt**: ...{result['text'][:200]}...\n\n"

        # Prepare next steps
        top_video = results[0]['video_id']

        suggestions = {
            f"/youtube:analyze '{top_video}'": "Analyze the top result in detail",
            "/youtube:export": "Generate research report",
            f"/youtube:research '{query}' --limit 20": "Expand search"
        }

        return format_prompt_response(
            content=content,
            suggestions=suggestions,
            data={
                "total_results": len(results),
                "query": query,
                "top_videos": [r['video_id'] for r in results[:5]]
            }
        )

    except Exception as e:
        return format_prompt_response(
            content=f"Error during research: {e!s}",
            suggestions={
                "/youtube:capabilities": "View capabilities",
                "/youtube:help": "Get help"
            }
        )


@mcp_prompt(
    name="youtube:help",
    description="Get context-aware help based on your current task",
    category="help",
    parameters={
        "context": {"type": "string", "description": "What you're trying to do"}
    }
)
async def get_help(context: str | None = None) -> str:
    """Provide context-aware help"""

    if not context:
        return format_prompt_response(
            content="""# YouTube Transcripts Help

## Common Tasks

### Finding Content
- Use `/youtube:find-transcripts` to browse available transcripts
- Filter by channel or date range

### Researching Topics  
- Use `/youtube:research 'your topic'` to search across all transcripts
- Add filters for more specific results

### Analyzing Transcripts
- Use `/youtube:analyze 'video_id'` for detailed analysis
- Extract citations, speakers, and key concepts

### Exporting Results
- Use `/youtube:export` to generate research reports
- Choose from multiple export formats

## Need More Help?
Describe what you're trying to do for specific guidance.
""",
            suggestions={
                "/youtube:capabilities": "View all capabilities",
                "/youtube:find-transcripts": "Start browsing content"
            }
        )

    # Provide context-specific help
    content = f"# Help: {context}\n\n"

    if "search" in context.lower() or "find" in context.lower():
        content += """## Searching for Content

1. **Browse Available Transcripts**
   ```
   /youtube:find-transcripts --channel "Lex Fridman"
   ```

2. **Search Specific Topics**
   ```
   /youtube:research "artificial intelligence ethics"
   ```

3. **Advanced Search**
   - Use filters for channel, date range
   - Combine multiple search terms
   - Use quotes for exact phrases
"""
    elif "analyze" in context.lower():
        content += """## Analyzing Transcripts

1. **Get Video ID**: Use `/youtube:find-transcripts` first
2. **Run Analysis**: `/youtube:analyze 'video_id'`
3. **Extract Specific Info**:
   - Citations and papers mentioned
   - Speaker identification
   - Key topics and themes
"""
    elif "export" in context.lower() or "report" in context.lower():
        content += """## Exporting Research

1. **Perform Research**: Use `/youtube:research` first
2. **Generate Report**: `/youtube:export`
3. **Available Formats**:
   - Markdown reports
   - JSON data export
   - CSV summaries
"""
    else:
        content += "Please try one of the suggested commands below."

    return format_prompt_response(
        content=content,
        suggestions={
            "/youtube:capabilities": "View all features",
            "/youtube:find-transcripts": "Start exploring"
        }
    )


def register_all_prompts():
    """Register all YouTube transcript prompts"""
    # The decorators automatically register prompts
    # This function ensures the module is imported
    registry = get_prompt_registry()

    # Add visual search prompts if available
    try:
        from .visual_prompts import analyze_video_visuals, find_code_snippets, view_code_snippet
        # Visual prompts are auto-registered via decorators
    except ImportError:
        pass  # Visual prompts not available yet

    return registry


# Validation
if __name__ == "__main__":
    import asyncio

    # Register prompts
    registry = register_all_prompts()

    # Test capabilities prompt
    result = asyncio.run(list_capabilities())
    assert "YouTube Transcripts MCP Server Capabilities" in result
    assert "/youtube:find-transcripts" in result

    # Verify all prompts registered
    prompts = registry.list_prompts()
    expected_prompts = [
        "youtube:capabilities",
        "youtube:find-transcripts",
        "youtube:research",
        "youtube:help"
    ]

    registered_names = [p.name for p in prompts]
    for expected in expected_prompts:
        assert expected in registered_names, f"Missing prompt: {expected}"

    print("✅ YouTube prompts validation passed")
