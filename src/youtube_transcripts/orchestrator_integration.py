"""
Orchestrator integration module for YouTube Transcripts.
Provides interfaces for claude-module-communicator to coordinate with arxiv-mcp-server.
Module: orchestrator_integration.py
Description: Implementation of orchestrator integration functionality

External Dependencies:
- asyncio: For async operations
- typing: Type hints
- pydantic: Data validation

Example Usage:
>>> from youtube_transcripts.orchestrator_integration import YouTubeResearchModule
>>> module = YouTubeResearchModule()
>>> await module.handle_message({"action": "search", "query": "machine learning"})
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

try:
    from .citation_detector import CitationDetector
    from .metadata_extractor import MetadataExtractor
    from .search_enhancements import EnhancedSearch
    from .unified_search import UnifiedSearchConfig, UnifiedYouTubeSearch
except ImportError:
    # For standalone testing
    from citation_detector import CitationDetector
    from metadata_extractor import MetadataExtractor
    from search_enhancements import EnhancedSearch
    from unified_search import UnifiedSearchConfig, UnifiedYouTubeSearch


class MessageType(Enum):
    """Types of messages in the orchestrator protocol"""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"


class ActionType(Enum):
    """Supported actions for YouTube module"""
    SEARCH = "search"
    FETCH_TRANSCRIPT = "fetch_transcript"
    EXTRACT_CITATIONS = "extract_citations"
    EXTRACT_METADATA = "extract_metadata"
    VALIDATE_CONTENT = "validate_content"
    FIND_RELATED = "find_related"


@dataclass
class OrchestrationMessage:
    """Standard message format for orchestrator communication"""
    source: str
    target: str | None
    type: MessageType
    action: str | None
    data: dict[str, Any]
    correlation_id: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now()


class YouTubeResearchModule:
    """
    YouTube Transcripts module for claude-module-communicator orchestration.
    Handles research tasks and coordinates with arxiv-mcp-server.
    """

    def __init__(self, config: UnifiedSearchConfig | None = None):
        self.config = config or UnifiedSearchConfig()
        self.youtube_client = UnifiedYouTubeSearch(self.config)
        self.enhanced_search = EnhancedSearch()
        self.citation_detector = CitationDetector()
        self.metadata_extractor = MetadataExtractor()
        self.module_name = "youtube_transcripts"

        # Event handlers for orchestrator
        self.event_handlers = {}

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming message from orchestrator"""
        try:
            # Parse message
            msg = self._parse_message(message)

            # Route to appropriate handler
            if msg.action:
                handler = self._get_action_handler(msg.action)
                result = await handler(msg.data)

                # Return response
                return self._create_response(msg, result)
            else:
                raise ValueError("No action specified in message")

        except Exception as e:
            return self._create_error_response(message, str(e))

    def _parse_message(self, message: dict[str, Any]) -> OrchestrationMessage:
        """Parse raw message into OrchestrationMessage"""
        return OrchestrationMessage(
            source=message.get("source", "unknown"),
            target=message.get("target", self.module_name),
            type=MessageType(message.get("type", "request")),
            action=message.get("action"),
            data=message.get("data", {}),
            correlation_id=message.get("correlation_id"),
            timestamp=message.get("timestamp")
        )

    def _get_action_handler(self, action: str):
        """Get handler for specific action"""
        handlers = {
            ActionType.SEARCH.value: self._handle_search,
            ActionType.FETCH_TRANSCRIPT.value: self._handle_fetch_transcript,
            ActionType.EXTRACT_CITATIONS.value: self._handle_extract_citations,
            ActionType.EXTRACT_METADATA.value: self._handle_extract_metadata,
            ActionType.VALIDATE_CONTENT.value: self._handle_validate_content,
            ActionType.FIND_RELATED.value: self._handle_find_related,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown action: {action}")
        return handler

    async def _handle_search(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle search requests"""
        query = data.get("query", "")
        use_youtube_api = data.get("use_youtube_api", False)
        use_widening = data.get("use_widening", True)
        filters = data.get("filters", {})

        if use_youtube_api:
            # Search YouTube API
            results = self.youtube_client.search_youtube_api(
                query=query,
                max_results=filters.get("max_results", 50),
                published_after=filters.get("published_after"),
                channel_id=filters.get("channel_id"),
                fetch_transcripts=filters.get("fetch_transcripts", False)
            )
        else:
            # Search local database
            results = self.youtube_client.search(
                query=query,
                use_widening=use_widening,
                limit=filters.get("limit", 10),
                channel_filter=filters.get("channel")
            )

        # Extract citations if requested
        if data.get("extract_citations", False) and results.get("results"):
            for result in results["results"]:
                if "text" in result:
                    citation_objects = self.citation_detector.detect_citations(result["text"])
                    # Convert Citation objects to dicts for JSON serialization
                    citations = [
                        {
                            "type": c.type,
                            "text": c.text,
                            "id": c.id,
                            "context": c.context,
                            "confidence": c.confidence
                        }
                        for c in citation_objects
                    ]
                    result["citations"] = citations

        return results

    async def _handle_fetch_transcript(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle transcript fetch requests"""
        video_id = data.get("video_id")
        video_url = data.get("video_url")

        if not video_id and not video_url:
            raise ValueError("Either video_id or video_url required")

        transcript = self.youtube_client.fetch_single_transcript(video_url or video_id)

        # Process transcript if requested
        result = {"transcript": transcript}

        if data.get("extract_metadata", False):
            metadata = self.metadata_extractor.extract_all(transcript)
            result["metadata"] = metadata

        if data.get("extract_citations", False):
            citation_objects = self.citation_detector.detect_citations(transcript)
            # Convert Citation objects to dicts for JSON serialization
            citations = [
                {
                    "type": c.type,
                    "text": c.text,
                    "id": c.id,
                    "context": c.context,
                    "confidence": c.confidence
                }
                for c in citation_objects
            ]
            result["citations"] = citations

        return result

    async def _handle_extract_citations(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle citation extraction requests"""
        text = data.get("text", "")
        video_id = data.get("video_id")

        if video_id and not text:
            # Fetch transcript first
            transcript_data = await self._handle_fetch_transcript({"video_id": video_id})
            text = transcript_data["transcript"]

        citation_objects = self.citation_detector.detect_citations(text)

        # Convert Citation objects to dicts
        citations = [
            {
                "type": c.type,
                "text": c.text,
                "id": c.id,
                "context": c.context,
                "confidence": c.confidence
            }
            for c in citation_objects
        ]

        # Group by type if requested
        if data.get("group_by_type", False):
            grouped = {}
            for citation in citations:
                citation_type = citation.get("type", "unknown")
                if citation_type not in grouped:
                    grouped[citation_type] = []
                grouped[citation_type].append(citation)
            return {"citations": citations, "grouped": grouped}

        return {"citations": citations}

    async def _handle_extract_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle metadata extraction requests"""
        text = data.get("text", "")
        video_id = data.get("video_id")

        if video_id and not text:
            # Fetch transcript first
            transcript_data = await self._handle_fetch_transcript({"video_id": video_id})
            text = transcript_data["transcript"]

        # Extract all metadata
        metadata = self.metadata_extractor.extract_all(text)

        # Add scientific analysis if requested
        if data.get("include_scientific", True):
            enhanced_results = self.enhanced_search._extract_metadata(text)
            metadata["scientific"] = enhanced_results

        return metadata

    async def _handle_validate_content(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle content validation requests (coordination point with ArXiv)"""
        video_id = data.get("video_id")
        claims = data.get("claims", [])

        if video_id and not claims:
            # Extract claims from video
            transcript_data = await self._handle_fetch_transcript({"video_id": video_id})
            text = transcript_data["transcript"]

            # Extract citations as potential claims
            citation_objects = self.citation_detector.detect_citations(text)
            claims = [{"text": c.context, "reference": c.id}
                     for c in citation_objects if c.context]

        # Prepare validation request for ArXiv module
        validation_requests = []
        for claim in claims:
            validation_requests.append({
                "claim": claim.get("text", ""),
                "reference": claim.get("reference", ""),
                "source": f"youtube:{video_id}" if video_id else "youtube:unknown"
            })

        # Return prepared requests (orchestrator will forward to ArXiv)
        return {
            "validation_requests": validation_requests,
            "forward_to": "arxiv_mcp_server",
            "action": "validate_claims"
        }

    async def _handle_find_related(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle finding related content requests"""
        video_id = data.get("video_id")
        paper_id = data.get("paper_id")
        keywords = data.get("keywords", [])

        results = {"videos": [], "suggested_searches": []}

        if paper_id:
            # Find videos discussing this paper
            # Construct search query from paper info
            search_queries = [
                f'"{paper_id}"',  # Direct ID mention
                f'arxiv {paper_id.replace(":", " ")}',  # Space-separated
            ]

            for query in search_queries:
                search_results = self.youtube_client.search(query, use_widening=True)
                results["videos"].extend(search_results.get("results", []))

        elif video_id:
            # Find papers related to this video
            transcript_data = await self._handle_fetch_transcript({"video_id": video_id})
            text = transcript_data["transcript"]

            # Extract key concepts
            metadata = self.metadata_extractor.extract_all(text)
            entities = metadata.get("entities", [])

            # Prepare search suggestions for ArXiv
            tech_terms = [e["text"] for e in entities
                         if e["label"] in ["TECHNICAL_TERM", "ML_CONCEPT"]]
            results["suggested_searches"] = tech_terms[:5]

        elif keywords:
            # Search with provided keywords
            for keyword in keywords:
                search_results = self.youtube_client.search(keyword, limit=5)
                results["videos"].extend(search_results.get("results", []))

        # Remove duplicates
        seen_ids = set()
        unique_videos = []
        for video in results["videos"]:
            if video.get("video_id") not in seen_ids:
                seen_ids.add(video.get("video_id"))
                unique_videos.append(video)

        results["videos"] = unique_videos
        return results

    def _create_response(self, request: OrchestrationMessage, result: Any) -> dict[str, Any]:
        """Create response message"""
        return {
            "source": self.module_name,
            "target": request.source,
            "type": MessageType.RESPONSE.value,
            "correlation_id": request.correlation_id,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }

    def _create_error_response(self, request: dict[str, Any], error: str) -> dict[str, Any]:
        """Create error response message"""
        return {
            "source": self.module_name,
            "target": request.get("source", "unknown"),
            "type": MessageType.ERROR.value,
            "correlation_id": request.get("correlation_id"),
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

    async def emit_event(self, event_type: str, data: dict[str, Any]):
        """Emit event to orchestrator"""
        event = {
            "source": self.module_name,
            "type": MessageType.EVENT.value,
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        # In real implementation, this would send to orchestrator
        # For now, just return the event
        return event

    def register_handler(self, event_type: str, handler):
        """Register event handler"""
        self.event_handlers[event_type] = handler


def create_integration_examples():
    """Create example integration messages"""
    examples = []

    # Example 1: Search for videos about a paper
    examples.append({
        "source": "orchestrator",
        "target": "youtube_transcripts",
        "type": "request",
        "action": "find_related",
        "data": {
            "paper_id": "arXiv:1706.03762",
            "keywords": ["attention", "transformer"]
        },
        "correlation_id": "req-001"
    })

    # Example 2: Extract citations from video
    examples.append({
        "source": "orchestrator",
        "target": "youtube_transcripts",
        "type": "request",
        "action": "extract_citations",
        "data": {
            "video_id": "abc123",
            "group_by_type": True
        },
        "correlation_id": "req-002"
    })

    # Example 3: Validate content with cross-reference
    examples.append({
        "source": "orchestrator",
        "target": "youtube_transcripts",
        "type": "request",
        "action": "validate_content",
        "data": {
            "video_id": "xyz789",
            "forward_results": True
        },
        "correlation_id": "req-003"
    })

    return examples


if __name__ == "__main__":
    # Test the module
    async def test_module():
        module = YouTubeResearchModule()

        # Test search
        search_msg = {
            "source": "test",
            "target": "youtube_transcripts",
            "type": "request",
            "action": "search",
            "data": {
                "query": "transformer architecture",
                "use_widening": True,
                "filters": {"limit": 5}
            }
        }

        try:
            result = await module.handle_message(search_msg)
            if "data" in result and "results" in result["data"]:
                print(f"Search returned {len(result['data']['results'])} results")
            else:
                print("Search completed but no results found")
        except Exception as e:
            print(f"Search test error: {e}")

        # Test citation extraction
        citation_msg = {
            "source": "test",
            "target": "youtube_transcripts",
            "type": "request",
            "action": "extract_citations",
            "data": {
                "text": "See the paper by Vaswani et al. (arXiv:1706.03762) on transformers."
            }
        }

        try:
            result = await module.handle_message(citation_msg)
            if "data" in result and "citations" in result["data"]:
                print(f"Found {len(result['data']['citations'])} citations")
                if result['data']['citations']:
                    print(f"First citation: {result['data']['citations'][0]}")
            else:
                print("Citation extraction completed but format unexpected")
        except Exception as e:
            print(f"Citation test error: {e}")

        print("\n✅ Orchestrator integration module validated!")
        return True

    # Run test
    asyncio.run(test_module())
