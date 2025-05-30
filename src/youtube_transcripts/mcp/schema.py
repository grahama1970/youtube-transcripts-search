# youtube_transcripts/mcp/schema.py
schema = {
    "name": "youtube-transcripts",
    "version": "1.0.0",
    "description": "Search and query YouTube transcripts using Gemini",
    "tools": [
        {
            "name": "search_transcripts",
            "description": "Search through YouTube transcripts using semantic search",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Filter by channel URLs"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch_transcripts",
            "description": "Fetch and store new transcripts from YouTube channels",
            "input_schema": {
                "type": "object",
                "properties": {
                    "channel_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "YouTube channel URLs"
                    },
                    "date_cutoff": {
                        "type": "string",
                        "description": "Date cutoff (e.g., '2025-01-01' or '6 months')"
                    },
                    "cleanup_months": {
                        "type": "integer",
                        "description": "Remove transcripts older than this many months"
                    }
                },
                "required": ["channel_urls"]
            }
        },
        {
            "name": "query_transcripts",
            "description": "Query transcripts using Gemini to answer questions",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to answer"
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Filter by channel URLs"
                    },
                    "max_context_videos": {
                        "type": "integer",
                        "description": "Max videos to use as context",
                        "default": 5
                    }
                },
                "required": ["question"]
            }
        }
    ]
}
