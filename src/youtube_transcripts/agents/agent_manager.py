"""
Module: agent_manager.py
Description: Implementation of agent manager functionality

External Dependencies:
- asyncio: [Documentation URL]
- enum: [Documentation URL]
- aiosqlite: [Documentation URL]
- : [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

import aiosqlite


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

class AgentType(Enum):
    TRANSCRIPT_FETCHER = "transcript_fetcher"
    SEARCH_OPTIMIZER = "search_optimizer"
    CONTENT_ANALYZER = "content_analyzer"
    RESEARCH_VALIDATOR = "research_validator"
    ORCHESTRATOR = "orchestrator"

class AsyncAgentManager:
    def __init__(self, db_path: str = "agents.db", max_concurrent: int = 5):
        self.db_path = db_path
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.running_tasks: dict[str, asyncio.Task] = {}

    async def submit_task(self, agent_type: AgentType, config: dict[str, Any]) -> str:
        """Submit a task for background execution"""
        task_id = str(uuid.uuid4())

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO agent_tasks (task_id, agent_type, config) 
                   VALUES (?, ?, ?)""",
                (task_id, agent_type.value, json.dumps(config))
            )
            await db.commit()

        # Create background task
        task = asyncio.create_task(self._execute_agent_task(task_id, agent_type, config))
        self.running_tasks[task_id] = task

        return task_id

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        """Get current status of a task"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT status, progress, result, error, created_at, completed_at 
                   FROM agent_tasks WHERE task_id = ?""",
                (task_id,)
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return {
            "task_id": task_id,
            "status": row[0],
            "progress": row[1],
            "result": json.loads(row[2]) if row[2] else None,
            "error": row[3],
            "created_at": row[4],
            "completed_at": row[5]
        }

    async def wait_for_task(self, task_id: str, timeout: int = 300) -> dict[str, Any]:
        """Wait for task completion with timeout"""
        start_time = datetime.now()

        while (datetime.now() - start_time).seconds < timeout:
            status = await self.get_status(task_id)

            if not status:
                raise ValueError(f"Task {task_id} not found")

            if status["status"] in ["COMPLETED", "FAILED", "TIMEOUT", "CANCELLED"]:
                return status

            await asyncio.sleep(1)

        # Timeout reached
        await self.cancel_task(task_id)
        return await self.get_status(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE agent_tasks SET status = ?, completed_at = CURRENT_TIMESTAMP 
                   WHERE task_id = ? AND status IN ('PENDING', 'RUNNING')""",
                (TaskStatus.CANCELLED.value, task_id)
            )
            await db.commit()

        return True

    async def _execute_agent_task(self, task_id: str, agent_type: AgentType, config: dict[str, Any]):
        """Execute agent task with semaphore control"""
        async with self.semaphore:
            try:
                # Update status to running
                await self._update_task_status(task_id, TaskStatus.RUNNING)

                # Route to appropriate agent
                if agent_type == AgentType.TRANSCRIPT_FETCHER:
                    from .transcript_fetcher_agent import TranscriptFetcherAgent
                    agent = TranscriptFetcherAgent()
                    result = await agent.execute(task_id, config)
                elif agent_type == AgentType.SEARCH_OPTIMIZER:
                    from .search_optimizer_agent import SearchOptimizerAgent
                    agent = SearchOptimizerAgent()
                    result = await agent.execute(task_id, config)
                elif agent_type == AgentType.CONTENT_ANALYZER:
                    from .content_analyzer_agent import ContentAnalyzerAgent
                    agent = ContentAnalyzerAgent()
                    result = await agent.execute(task_id, config)
                elif agent_type == AgentType.ORCHESTRATOR:
                    from .orchestrator_agent import OrchestratorAgent
                    agent = OrchestratorAgent()
                    result = await agent.execute(task_id, config)
                else:
                    raise ValueError(f"Unknown agent type: {agent_type}")

                # Update with result
                await self._update_task_status(
                    task_id, TaskStatus.COMPLETED, result=result
                )

            except asyncio.CancelledError:
                await self._update_task_status(task_id, TaskStatus.CANCELLED)
            except Exception as e:
                await self._update_task_status(
                    task_id, TaskStatus.FAILED, error=str(e)
                )
            finally:
                self.running_tasks.pop(task_id, None)

    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Any = None,
        error: str = None,
        progress: float = None
    ):
        """Update task status in database"""
        async with aiosqlite.connect(self.db_path) as db:
            updates = ["status = ?"]
            params = [status.value]

            if status == TaskStatus.RUNNING:
                updates.append("started_at = CURRENT_TIMESTAMP")
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                updates.append("completed_at = CURRENT_TIMESTAMP")

            if result is not None:
                updates.append("result = ?")
                params.append(json.dumps(result))

            if error is not None:
                updates.append("error = ?")
                params.append(error)

            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)

            params.append(task_id)

            await db.execute(
                f"UPDATE agent_tasks SET {', '.join(updates)} WHERE task_id = ?",
                params
            )
            await db.commit()
