"""
Module: debug_import.py
Description: Module for debug import functionality

External Dependencies:
- youtube_transcripts: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

#!/usr/bin/env python3
"""Debug import issues"""

import sys
import os
from pathlib import Path

print("Current working directory:", os.getcwd())
print("\nPython path:")
for p in sys.path:
    print(f"  - {p}")

print("\nTrying to import youtube_transcripts...")
try:
    import youtube_transcripts
    print(f"✅ youtube_transcripts imported from: {youtube_transcripts.__file__}")
except Exception as e:
    print(f"❌ Failed to import youtube_transcripts: {e}")

print("\nTrying to import youtube_transcripts.agents...")
try:
    import youtube_transcripts.agents
    print(f"✅ youtube_transcripts.agents imported")
except Exception as e:
    print(f"❌ Failed to import youtube_transcripts.agents: {e}")

print("\nTrying to import youtube_transcripts.agents.agent_manager...")
try:
    from youtube_transcripts.agents.agent_manager import AsyncAgentManager
    print(f"✅ AsyncAgentManager imported successfully")
except Exception as e:
    print(f"❌ Failed to import AsyncAgentManager: {e}")

# Check if the files exist
src_path = Path(__file__).parent / "src"
print(f"\nChecking files in {src_path}:")
agents_path = src_path / "youtube_transcripts" / "agents"
if agents_path.exists():
    print(f"✅ {agents_path} exists")
    for f in agents_path.glob("*.py"):
        print(f"  - {f.name}")
else:
    print(f"❌ {agents_path} does not exist")