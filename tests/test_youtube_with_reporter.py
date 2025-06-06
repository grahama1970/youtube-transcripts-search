#!/usr/bin/env python
"""Test YouTube Transcripts module with pytest reporter"""
import subprocess
import sys
import os

# Create test file content that imports correctly
test_content = '''import pytest
import asyncio
import sys
import os

# Add src to path BEFORE imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Now we can import
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
        assert module.version == "1.0.0"
        assert len(module.capabilities) == 5
    
    @pytest.mark.asyncio
    async def test_standardized_response_format(self, module):
        """Test module returns standardized response with data key"""
        request = {
            "action": "fetch_transcript",
            "data": {"video_id": "test_video_123"}
        }
        
        response = await module.process(request)
        
        assert response["success"] is True
        assert "data" in response
        assert isinstance(response["data"], dict)
        assert response["data"]["video_id"] == "test_video_123"
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, module):
        """Test error responses follow standard format"""
        request = {
            "action": "unknown_action",
            "data": {}
        }
        
        response = await module.process(request)
        
        assert response["success"] is False
        assert "error" in response
        assert "data" not in response
'''

# Write test file
with open('test_youtube_reporter.py', 'w') as f:
    f.write(test_content)

# Run pytest with reporter
cmd = [
    sys.executable, '-m', 'pytest',
    'test_youtube_reporter.py',
    '-v',
    '--claude-reporter',
    '--claude-model=youtube_transcripts',
    '--claude-output-dir=test_reports'
]

print("Running: " + " ".join(cmd))
result = subprocess.run(cmd, capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Check if report was created
if os.path.exists('test_reports/youtube_transcripts_test_report.txt'):
    print("\nTest report content:")
    with open('test_reports/youtube_transcripts_test_report.txt', 'r') as f:
        print(f.read())

# Clean up
os.remove('test_youtube_reporter.py')

sys.exit(result.returncode)
