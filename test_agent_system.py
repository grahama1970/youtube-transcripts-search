#!/usr/bin/env python3
"""
Test script for Task 003: Agent System Implementation
Tests the autonomous agent framework functionality
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from src.youtube_transcripts.agents.agent_manager import AsyncAgentManager, AgentType, TaskStatus
from src.youtube_transcripts.agents.base_agent import BaseAgent

async def test_agent_system():
    """Test the agent system implementation"""
    print("\n" + "="*50)
    print("Testing Agent System Implementation")
    print("="*50)
    
    manager = AsyncAgentManager()
    
    # Test 1: Submit and check task status
    print("\n1. Testing task submission and status:")
    task_id = await manager.submit_task(
        AgentType.SEARCH_OPTIMIZER,
        {"action": "optimize_queries", "queries": ["VERL tutorial", "reinforcement learning"]}
    )
    print(f"   ✅ Task submitted: {task_id}")
    
    # Check immediate status
    status = await manager.get_status(task_id)
    print(f"   Status: {status['status']}")
    print(f"   Progress: {status['progress']}%")
    
    # Test 2: Wait for task completion
    print("\n2. Testing task completion:")
    result = await manager.wait_for_task(task_id, timeout=30)
    print(f"   Status: {result['status']}")
    if result['status'] == 'COMPLETED':
        print(f"   ✅ Task completed successfully")
        if result['result']:
            print(f"   Optimized {len(result['result']['optimized_queries'])} queries")
            print(f"   Average expansion ratio: {result['result']['average_expansion_ratio']:.2f}")
    
    # Test 3: Test orchestrator workflow
    print("\n3. Testing orchestrator workflow:")
    orch_task_id = await manager.submit_task(
        AgentType.ORCHESTRATOR,
        {"workflow": "daily_update", "channels": ["test_channel"]}
    )
    print(f"   ✅ Orchestrator task submitted: {orch_task_id}")
    
    # Monitor progress
    for i in range(5):
        await asyncio.sleep(2)
        status = await manager.get_status(orch_task_id)
        print(f"   Progress: {status['progress']:.0f}%")
        if status['status'] in ['COMPLETED', 'FAILED']:
            break
    
    # Test 4: Test inter-agent messaging
    print("\n4. Testing agent communication:")
    
    class TestAgent(BaseAgent):
        async def execute(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
            return {"test": "result"}
    
    agent1 = TestAgent()
    agent1.agent_id = "TestAgent1"
    
    agent2 = TestAgent()
    agent2.agent_id = "TestAgent2"
    
    # Send message
    message_id = await agent1.send_message(
        "TestAgent2",
        {"action": "test", "data": "Hello from Agent1"}
    )
    print(f"   ✅ Message sent: {message_id}")
    
    # Receive message
    messages = await agent2.receive_messages()
    if messages:
        print(f"   ✅ Message received: {messages[0]['content']['data']}")
    
    # Test 5: Multiple concurrent tasks
    print("\n5. Testing concurrent task execution:")
    tasks = []
    for i in range(3):
        task_id = await manager.submit_task(
            AgentType.SEARCH_OPTIMIZER,
            {"action": "optimize_queries", "queries": [f"query {i}"]}
        )
        tasks.append(task_id)
    
    print(f"   ✅ Submitted {len(tasks)} concurrent tasks")
    
    # Wait for all to complete
    results = await asyncio.gather(*[
        manager.wait_for_task(tid, timeout=30) for tid in tasks
    ])
    
    completed = sum(1 for r in results if r['status'] == 'COMPLETED')
    print(f"   ✅ {completed}/{len(tasks)} tasks completed successfully")
    
    print("\n" + "="*50)
    print("✅ Agent system tests completed!")
    print("="*50)

async def test_database_operations():
    """Test database operations directly"""
    print("\n6. Testing database operations:")
    
    import aiosqlite
    async with aiosqlite.connect("agents.db") as db:
        # Check tables exist
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = await cursor.fetchall()
        print(f"   Tables: {[t[0] for t in tables]}")
        
        # Check task count
        cursor = await db.execute("SELECT COUNT(*) FROM agent_tasks")
        count = await cursor.fetchone()
        print(f"   Total tasks in database: {count[0]}")

if __name__ == "__main__":
    # Ensure database is initialized
    import sqlite3
    conn = sqlite3.connect("agents.db")
    conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
    conn.close()
    
    # Run tests
    asyncio.run(test_agent_system())
    asyncio.run(test_database_operations())