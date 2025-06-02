# youtube_transcripts/mcp/schema.py
from typing import Dict, Any
from ..cli.schemas import Transcript, QueryResult

def get_mcp_schemas() -> Dict[str, Dict[str, Any]]:
    """Generate MCP-compliant JSON schemas for CLI commands."""
    return {
        "fetch": {
            "description": "Fetch and store YouTube transcripts with a date cutoff.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "channels": {
                        "type": "string",
                        "description": "Comma-separated YouTube channel URLs"
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
                "required": ["channels", "date_cutoff", "cleanup_months"]
            }
        },
        "query": {
            "description": "Query transcripts to answer a question using Gemini.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Query to answer using transcripts"
                    },
                    "channels": {
                        "type": "string",
                        "description": "Comma-separated YouTube channel URLs"
                    }
                },
                "required": ["question", "channels"]
            }
        }
    }

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Validate MCP schemas
    total_tests += 1
    try:
        schemas = get_mcp_schemas()
        if "fetch" not in schemas or "query" not in schemas:
            all_validation_failures.append("Missing required schemas")
        if not all("inputSchema" in schema for schema in schemas.values()):
            all_validation_failures.append("Schemas missing inputSchema")
    except Exception as e:
        all_validation_failures.append(f"MCP schema generation failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
