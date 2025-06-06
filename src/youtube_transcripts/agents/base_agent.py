"""
Module: base_agent.py
Description: Implementation of base agent functionality

External Dependencies:
- abc: [Documentation URL]
- aiosqlite: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import aiosqlite


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, db_path: str = "agents.db"):
        self.db_path = db_path
        self.agent_id = self.__class__.__name__

    @abstractmethod
    async def execute(self, task_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's main task"""
        pass

    async def update_progress(self, task_id: str, progress: float, message: str = None):
        """Update task progress"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE agent_tasks SET progress = ? WHERE task_id = ?",
                (progress, task_id)
            )
            if message:
                metadata = json.dumps({"last_message": message, "timestamp": datetime.now().isoformat()})
                await db.execute(
                    "UPDATE agent_tasks SET metadata = ? WHERE task_id = ?",
                    (metadata, task_id)
                )
            await db.commit()

    async def send_message(self, to_agent: str, content: dict[str, Any], task_id: str = None):
        """Send message to another agent"""
        message_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO agent_messages (message_id, from_agent, to_agent, task_id, content)
                   VALUES (?, ?, ?, ?, ?)""",
                (message_id, self.agent_id, to_agent, task_id, json.dumps(content))
            )
            await db.commit()
        return message_id

    async def receive_messages(self) -> list[dict[str, Any]]:
        """Receive pending messages for this agent"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT message_id, from_agent, content, task_id, created_at 
                   FROM agent_messages 
                   WHERE to_agent = ? AND processed = FALSE
                   ORDER BY created_at""",
                (self.agent_id,)
            )
            messages = []
            async for row in cursor:
                messages.append({
                    "message_id": row[0],
                    "from_agent": row[1],
                    "content": json.loads(row[2]),
                    "task_id": row[3],
                    "created_at": row[4]
                })

            # Mark as processed
            if messages:
                message_ids = [m["message_id"] for m in messages]
                placeholders = ",".join("?" for _ in message_ids)
                await db.execute(
                    f"UPDATE agent_messages SET processed = TRUE WHERE message_id IN ({placeholders})",
                    message_ids
                )
                await db.commit()

        return messages
