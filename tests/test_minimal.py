"""Minimal test to debug import issues"""

def test_basic():
    """Test that doesn't import anything"""
    assert 1 + 1 == 2

def test_import_youtube_transcripts():
    """Test importing main package"""
    import youtube_transcripts
    assert youtube_transcripts.__version__ == "0.1.0"

def test_import_agents():
    """Test importing agents subpackage"""
    import youtube_transcripts.agents
    assert hasattr(youtube_transcripts.agents, 'AsyncAgentManager')

def test_import_agent_manager():
    """Test importing from agent_manager"""
    from youtube_transcripts.agents.agent_manager import AsyncAgentManager, AgentType, TaskStatus
    assert AsyncAgentManager is not None
    assert AgentType is not None
    assert TaskStatus is not None