"""Level 0 tests for YouTube Transcripts module - Basic functionality and standardization compliance"""
import pytest
import asyncio
import os
import sys

# Add parent directories to path
test_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.dirname(test_dir)
project_dir = os.path.dirname(tests_dir)
src_dir = os.path.join(project_dir, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Now import the module
from youtube_transcripts.integrations.youtube_transcripts_module import YoutubeTranscriptsModule


class TestYoutubeTranscriptsStandardized:
    """Test YouTube Transcripts module follows standardized format"""
    
    @pytest.fixture
    async def module(self):
        """Create and start module instance"""
        module = YoutubeTranscriptsModule()
        await module.start()
        yield module
        await module.stop()
    
    @pytest.mark.asyncio
    async def test_module_attributes(self, module):
        """Test module has required attributes"""
        assert module.name == "youtube_transcripts"
        assert hasattr(module, "version")
        assert hasattr(module, "description")
        assert hasattr(module, "capabilities")
        assert isinstance(module.capabilities, list)
        assert len(module.capabilities) == 5
        assert "fetch_transcript" in module.capabilities
        assert "search_transcripts" in module.capabilities
        assert "get_channel_videos" in module.capabilities
        assert "extract_keywords" in module.capabilities
        assert "summarize_video" in module.capabilities
    
    @pytest.mark.asyncio
    async def test_standardized_response_format(self, module):
        """Test module returns standardized response with data key"""
        # Test valid action
        request = {
            "action": "fetch_transcript",
            "data": {"video_id": "test_video_123"}
        }
        
        response = await module.process(request)
        
        # Check standardized format
        assert "success" in response
        assert "module" in response
        assert response["success"] is True
        assert response["module"] == "youtube_transcripts"
        
        # CRITICAL: Check data is nested under 'data' key
        assert "data" in response
        assert isinstance(response["data"], dict)
        
        # Check actual data content
        assert "video_id" in response["data"]
        assert "transcript" in response["data"]
        assert response["data"]["video_id"] == "test_video_123"
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, module):
        """Test error responses follow standard format"""
        # Test unknown action
        request = {
            "action": "unknown_action",
            "data": {}
        }
        
        response = await module.process(request)
        
        # Check error format
        assert response["success"] is False
        assert "error" in response
        assert "module" in response
        assert response["module"] == "youtube_transcripts"
        
        # Error responses should NOT have data key
        assert "data" not in response
    
    @pytest.mark.asyncio
    async def test_fetch_transcript_missing_params(self, module):
        """Test fetch_transcript with missing parameters"""
        request = {
            "action": "fetch_transcript",
            "data": {}  # Missing video_id
        }
        
        response = await module.process(request)
        
        assert response["success"] is False
        assert "error" in response
        assert "video_id" in response["error"].lower()
    
    @pytest.mark.asyncio
    async def test_search_transcripts(self, module):
        """Test search transcripts functionality"""
        request = {
            "action": "search_transcripts",
            "data": {
                "query": "machine learning",
                "limit": 5
            }
        }
        
        response = await module.process(request)
        
        assert response["success"] is True
        assert "data" in response
        assert "query" in response["data"]
        assert "results" in response["data"]
        assert "total_results" in response["data"]
        assert response["data"]["query"] == "machine learning"
        assert response["data"]["limit"] == 5
    
    @pytest.mark.asyncio
    async def test_get_channel_videos(self, module):
        """Test getting channel videos"""
        request = {
            "action": "get_channel_videos",
            "data": {
                "channel_id": "UC_test_channel"
            }
        }
        
        response = await module.process(request)
        
        assert response["success"] is True
        assert "data" in response
        assert "channel_id" in response["data"]
        assert "videos" in response["data"]
        assert "total_videos" in response["data"]
        assert response["data"]["channel_id"] == "UC_test_channel"
    
    @pytest.mark.asyncio
    async def test_extract_keywords_with_transcript(self, module):
        """Test keyword extraction with transcript"""
        request = {
            "action": "extract_keywords",
            "data": {
                "transcript": "This is a test transcript about machine learning and AI"
            }
        }
        
        response = await module.process(request)
        
        assert response["success"] is True
        assert "data" in response
        assert "keywords" in response["data"]
        assert "phrases" in response["data"]
        assert "topics" in response["data"]
        assert isinstance(response["data"]["keywords"], list)
    
    @pytest.mark.asyncio
    async def test_extract_keywords_with_video_id(self, module):
        """Test keyword extraction with video ID"""
        request = {
            "action": "extract_keywords",
            "data": {
                "video_id": "test_video_123"
            }
        }
        
        response = await module.process(request)
        
        assert response["success"] is True
        assert "data" in response
        assert "keywords" in response["data"]
    
    @pytest.mark.asyncio
    async def test_summarize_video_with_id(self, module):
        """Test video summarization with video ID"""
        request = {
            "action": "summarize_video",
            "data": {
                "video_id": "test_video_123",
                "summary_type": "detailed"
            }
        }
        
        response = await module.process(request)
        
        assert response["success"] is True
        assert "data" in response
        assert "summary" in response["data"]
        assert "summary_type" in response["data"]
        assert "key_points" in response["data"]
        assert response["data"]["summary_type"] == "detailed"
    
    @pytest.mark.asyncio
    async def test_summarize_video_missing_params(self, module):
        """Test summarize_video with missing parameters"""
        request = {
            "action": "summarize_video",
            "data": {}  # Missing both video_id and transcript
        }
        
        response = await module.process(request)
        
        assert response["success"] is False
        assert "error" in response
        assert ("video_id" in response["error"].lower() or 
                "transcript" in response["error"].lower())
    
    @pytest.mark.asyncio
    async def test_multiple_actions_sequence(self, module):
        """Test multiple actions in sequence maintain format"""
        actions = [
            ("fetch_transcript", {"video_id": "test1"}),
            ("search_transcripts", {"query": "AI"}),
            ("get_channel_videos", {"channel_id": "channel1"}),
        ]
        
        for action, data in actions:
            request = {"action": action, "data": data}
            response = await module.process(request)
            
            assert response["success"] is True
            assert response["module"] == "youtube_transcripts"
            assert "data" in response
            assert isinstance(response["data"], dict)


if __name__ == "__main__":
    # Run tests with detailed output
    import subprocess
    subprocess.run([
        "python", "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short",
        "--asyncio-mode=auto"
    ])
