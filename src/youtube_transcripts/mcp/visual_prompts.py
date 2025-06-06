"""
Visual content search prompts for YouTube transcripts MCP server
"""
Module: visual_prompts.py
Description: Functions for visual prompts operations
Description: Functions for visual prompts operations

from loguru import logger

from ..core.database import Database
from ..mcp.prompts import format_prompt_response, mcp_prompt
from ..visual_extractor import VisualExtractor


@mcp_prompt(
    name="youtube:find-code",
    description="Find code snippets in YouTube videos",
    category="visual",
    examples=[
        "Find Python code examples in machine learning tutorials",
        "Show terminal commands from Docker videos"
    ]
)
async def find_code_snippets(query: str, limit: int = 10, language: str | None = None) -> str:
    """
    Search for code snippets in YouTube videos using visual extraction
    
    Args:
        query: Search query for video content
        limit: Maximum number of results
        language: Filter by programming language (optional)
    """
    db = Database()
    extractor = VisualExtractor()

    # First, find relevant videos
    videos = await db.search_transcripts(query, limit=limit)

    results = []
    for video in videos:
        # Check if we have visual content cached
        visual_contents = await db.get_visual_contents(video['video_id'])

        if not visual_contents:
            # Extract on-demand (for demo - in production this would be pre-processed)
            logger.info(f"Extracting visual content for {video['video_id']}")
            frames = await extractor.extract_frames(video['video_id'], strategy="adaptive")
            visual_contents = await extractor.detect_code_content(frames)

            # Store for future use
            await db.store_visual_contents(video['video_id'], visual_contents)

        # Filter by language if specified
        if language:
            visual_contents = [vc for vc in visual_contents
                             if vc.language and language.lower() in vc.language.lower()]

        if visual_contents:
            results.append({
                'video_id': video['video_id'],
                'title': video['title'],
                'channel': video['channel_name'],
                'code_snippets': [
                    {
                        'timestamp': vc.frame.timecode,
                        'language': vc.language,
                        'preview': vc.extracted_text[:200] if vc.extracted_text else None,
                        'confidence': vc.confidence
                    }
                    for vc in visual_contents[:3]  # Top 3 snippets per video
                ]
            })

    # Format results
    content_parts = [f"Found {len(results)} videos with code snippets:\n"]

    for result in results:
        content_parts.append(f"\n📹 **{result['title']}**")
        content_parts.append(f"   Channel: {result['channel']}")
        content_parts.append("   Code snippets found:")

        for snippet in result['code_snippets']:
            lang = snippet['language'] or 'unknown'
            content_parts.append(f"   - [{snippet['timestamp']}] {lang} "
                               f"(confidence: {snippet['confidence']:.0%})")
            if snippet['preview']:
                preview = snippet['preview'].split('\n')[0]  # First line
                content_parts.append(f"     `{preview[:60]}...`")

    return format_prompt_response(
        content='\n'.join(content_parts),
        next_steps=[
            "Use /youtube:view-code to see full code snippet",
            "Use /youtube:analyze-video for complete visual analysis"
        ],
        suggestions={
            f"/youtube:view-code '{results[0]['video_id']}' --timestamp": "View specific code",
            "/youtube:find-code --language python": "Filter by language"
        },
        data={
            'videos': results,
            'total_snippets': sum(len(r['code_snippets']) for r in results)
        }
    )


@mcp_prompt(
    name="youtube:analyze-video",
    description="Analyze visual content of a YouTube video",
    category="visual"
)
async def analyze_video_visuals(video_id: str, content_types: list[str] | None = None) -> str:
    """
    Comprehensive visual analysis of a YouTube video
    
    Args:
        video_id: YouTube video ID
        content_types: Filter by types (code, terminal, chart, diagram)
    """
    db = Database()
    extractor = VisualExtractor()

    # Get video metadata
    video = await db.get_video_metadata(video_id)
    if not video:
        return format_prompt_response(
            content=f"Video {video_id} not found in database",
            suggestions={
                "/youtube:find-transcripts": "Search for videos"
            }
        )

    # Extract visual content
    logger.info(f"Analyzing visual content for {video_id}")
    frames = await extractor.extract_frames(video_id, strategy="adaptive")
    visual_contents = await extractor.detect_code_content(frames)

    # Filter by content types if specified
    if content_types:
        visual_contents = [vc for vc in visual_contents
                         if vc.content_type in content_types]

    # Group by content type
    by_type = {}
    for vc in visual_contents:
        if vc.content_type not in by_type:
            by_type[vc.content_type] = []
        by_type[vc.content_type].append(vc)

    # Build analysis report
    content_parts = [
        f"# Visual Analysis: {video['title']}\n",
        f"**Channel**: {video['channel_name']}",
        f"**Duration**: {video['duration']}",
        f"**Total visual elements**: {len(visual_contents)}\n"
    ]

    # Summary by type
    content_parts.append("## Content Summary")
    for content_type, items in by_type.items():
        content_parts.append(f"- **{content_type.title()}**: {len(items)} occurrences")

    # Detailed timeline
    content_parts.append("\n## Visual Timeline")

    for content_type, items in by_type.items():
        content_parts.append(f"\n### {content_type.title()} Content")

        for vc in items[:5]:  # Top 5 per type
            content_parts.append(f"\n**[{vc.frame.timecode}]** {content_type}")

            if vc.language:
                content_parts.append(f"Language: {vc.language}")

            if vc.extracted_text:
                # Show preview
                lines = vc.extracted_text.split('\n')[:3]
                content_parts.append("```" + (vc.language or ''))
                content_parts.extend(lines)
                content_parts.append("```")

    # Recommendations
    content_parts.append("\n## Insights")

    if 'code' in by_type:
        languages = set(vc.language for vc in by_type['code'] if vc.language)
        content_parts.append(f"- Programming languages detected: {', '.join(languages)}")
        content_parts.append(f"- Code segments appear at {len(by_type['code'])} points")

    if 'terminal' in by_type:
        content_parts.append(f"- Terminal/command line shown {len(by_type['terminal'])} times")

    return format_prompt_response(
        content='\n'.join(content_parts),
        next_steps=[
            "Use /youtube:export-code to save all code snippets",
            "Use /youtube:create-tutorial to generate tutorial from video"
        ],
        suggestions={
            f"/youtube:view-code '{video_id}' --all": "View all code snippets",
            f"/youtube:find-similar '{video_id}'": "Find similar videos"
        },
        data={
            'video_id': video_id,
            'visual_summary': {
                content_type: len(items)
                for content_type, items in by_type.items()
            },
            'languages': list(set(vc.language for vc in visual_contents if vc.language))
        }
    )


@mcp_prompt(
    name="youtube:view-code",
    description="View extracted code from a specific video timestamp",
    category="visual"
)
async def view_code_snippet(video_id: str,
                          timestamp: str | None = None,
                          all: bool = False) -> str:
    """
    View extracted code snippets from a video
    
    Args:
        video_id: YouTube video ID
        timestamp: Specific timestamp (HH:MM:SS format)
        all: Show all code snippets from video
    """
    db = Database()

    # Get visual contents
    visual_contents = await db.get_visual_contents(video_id)
    code_contents = [vc for vc in visual_contents if vc.content_type in ['code', 'terminal']]

    if not code_contents:
        return format_prompt_response(
            content=f"No code snippets found in video {video_id}",
            suggestions={
                f"/youtube:analyze-video '{video_id}'": "Analyze video for code"
            }
        )

    # Filter by timestamp if specified
    if timestamp and not all:
        # Parse timestamp
        target_seconds = parse_timestamp(timestamp)

        # Find closest code snippet
        closest = min(code_contents,
                     key=lambda vc: abs(vc.frame.timestamp - target_seconds))

        code_contents = [closest]
    elif not all:
        # Show first snippet by default
        code_contents = code_contents[:1]

    # Format code snippets
    content_parts = []

    for i, vc in enumerate(code_contents):
        if len(code_contents) > 1:
            content_parts.append(f"\n## Code Snippet {i+1}/{len(code_contents)}")

        content_parts.append(f"**Timestamp**: {vc.frame.timecode}")
        content_parts.append(f"**Type**: {vc.content_type}")

        if vc.language:
            content_parts.append(f"**Language**: {vc.language}")

        content_parts.append(f"**Confidence**: {vc.confidence:.0%}")

        if vc.extracted_text:
            content_parts.append(f"\n```{vc.language or ''}")
            content_parts.append(vc.extracted_text)
            content_parts.append("```")

        # Add transcript context
        transcript_context = await db.get_transcript_at_timestamp(
            video_id,
            vc.frame.timestamp
        )

        if transcript_context:
            content_parts.append("\n**Speaker context**:")
            content_parts.append(f"> {transcript_context}")

    video_url = f"https://youtube.com/watch?v={video_id}&t={int(code_contents[0].frame.timestamp)}"

    return format_prompt_response(
        content='\n'.join(content_parts),
        next_steps=[
            "Use /youtube:export-code to save to file",
            "Use /youtube:improve-code for AI enhancement"
        ],
        suggestions={
            f"/youtube:export-code '{video_id}'": "Export all code",
            video_url: "Watch at this timestamp"
        },
        data={
            'video_id': video_id,
            'snippets': [
                {
                    'timestamp': vc.frame.timestamp,
                    'timecode': vc.frame.timecode,
                    'language': vc.language,
                    'text': vc.extracted_text
                }
                for vc in code_contents
            ]
        }
    )


def parse_timestamp(timestamp: str) -> float:
    """Parse timestamp string (HH:MM:SS or MM:SS) to seconds"""
    parts = timestamp.split(':')
    if len(parts) == 3:
        h, m, s = map(int, parts)
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = map(int, parts)
        return m * 60 + s
    else:
        return float(timestamp)
