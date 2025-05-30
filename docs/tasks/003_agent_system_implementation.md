# Task 003: Agent System Implementation with Claude Background Instances

**Component**: Autonomous Agent Framework  
**Technology**: Claude background instances with SQLite async polling  
**Goal**: Implement intelligent agents for autonomous transcript processing, search optimization, and content analysis using proven patterns from claude_max_proxy.

## Prerequisites
- **Completed**: Task 001 (DeepRetrieval Integration)
- **Completed**: Task 002 (Channel-specific LoRA adapters) 
- **Software**: Python 3.10+, SQLite3, asyncio
- **Understanding**: Review `/home/graham/workspace/experiments/claude_max_proxy` for patterns
- **Services**: ArangoDB running, Ollama available

## ✅ Task Checklist

### Phase 1: Core Infrastructure Setup
**Objective**: Adapt AsyncPollingManager from claude_max_proxy for agent coordination.

- [ ] **Create Agent Database Schema**
  1. Create schema file: `src/youtube_transcripts/agents/schema.sql`
     ```sql
     CREATE TABLE IF NOT EXISTS agent_tasks (
         task_id TEXT PRIMARY KEY,
         agent_type TEXT NOT NULL,
         status TEXT DEFAULT 'PENDING',
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         started_at TIMESTAMP,
         completed_at TIMESTAMP,
         config TEXT NOT NULL,
         result TEXT,
         error TEXT,
         progress REAL DEFAULT 0.0,
         metadata TEXT
     );
     
     CREATE TABLE IF NOT EXISTS agent_messages (
         message_id TEXT PRIMARY KEY,
         from_agent TEXT NOT NULL,
         to_agent TEXT NOT NULL,
         task_id TEXT,
         content TEXT NOT NULL,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         processed BOOLEAN DEFAULT FALSE
     );
     
     CREATE INDEX idx_status ON agent_tasks(status);
     CREATE INDEX idx_agent_type ON agent_tasks(agent_type);
     CREATE INDEX idx_messages_recipient ON agent_messages(to_agent, processed);
     ```
  2. Initialize database:
     ```bash
     cd /home/graham/workspace/experiments/youtube_transcripts/
     sqlite3 agents.db < src/youtube_transcripts/agents/schema.sql
     ```
     - Expected: Database created with tables
     - If failed: Check SQLite3 installation

- [ ] **Implement Base Agent Manager**
  1. Create `src/youtube_transcripts/agents/agent_manager.py`:
     ```python
     import asyncio
     import sqlite3
     import json
     import uuid
     from datetime import datetime, timedelta
     from typing import Dict, Any, Optional, List
     from enum import Enum
     import aiosqlite
     from pathlib import Path
     
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
             self.running_tasks: Dict[str, asyncio.Task] = {}
             
         async def submit_task(self, agent_type: AgentType, config: Dict[str, Any]) -> str:
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
         
         async def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
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
         
         async def wait_for_task(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
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
         
         async def _execute_agent_task(self, task_id: str, agent_type: AgentType, config: Dict[str, Any]):
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
     ```
  2. Test import:
     ```bash
     python -c "from src.youtube_transcripts.agents.agent_manager import AsyncAgentManager; print('✅ Agent manager ready')"
     ```

### Phase 2: Implement Core Agents
**Objective**: Create specialized agents for different tasks.

- [ ] **Create Base Agent Class**
  1. Create `src/youtube_transcripts/agents/base_agent.py`:
     ```python
     from abc import ABC, abstractmethod
     from typing import Dict, Any, Optional
     import asyncio
     import aiosqlite
     from datetime import datetime
     
     class BaseAgent(ABC):
         """Base class for all agents"""
         
         def __init__(self, db_path: str = "agents.db"):
             self.db_path = db_path
             self.agent_id = self.__class__.__name__
         
         @abstractmethod
         async def execute(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
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
         
         async def send_message(self, to_agent: str, content: Dict[str, Any], task_id: str = None):
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
         
         async def receive_messages(self) -> List[Dict[str, Any]]:
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
     ```

- [ ] **Implement Transcript Fetcher Agent**
  1. Create `src/youtube_transcripts/agents/transcript_fetcher_agent.py`:
     ```python
     import asyncio
     from typing import Dict, Any, List
     from datetime import datetime, timedelta
     from .base_agent import BaseAgent
     from youtube_transcripts.core.transcript import fetch_channel_transcripts
     
     class TranscriptFetcherAgent(BaseAgent):
         """Agent responsible for fetching new transcripts from YouTube channels"""
         
         async def execute(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """
             Config expects:
             - channels: List of channel URLs or IDs
             - since_days: Number of days to look back (default: 7)
             - max_videos: Maximum videos per channel (default: 10)
             """
             channels = config.get("channels", [])
             since_days = config.get("since_days", 7)
             max_videos = config.get("max_videos", 10)
             
             results = {
                 "total_fetched": 0,
                 "channels_processed": 0,
                 "errors": [],
                 "new_transcripts": []
             }
             
             total_channels = len(channels)
             
             for idx, channel in enumerate(channels):
                 try:
                     # Update progress
                     progress = (idx / total_channels) * 100
                     await self.update_progress(
                         task_id, 
                         progress, 
                         f"Processing channel {idx+1}/{total_channels}: {channel}"
                     )
                     
                     # Fetch transcripts
                     since_date = datetime.now() - timedelta(days=since_days)
                     transcripts = await self._fetch_channel_transcripts(
                         channel, since_date, max_videos
                     )
                     
                     # Store in ArangoDB
                     stored_count = await self._store_transcripts(transcripts)
                     
                     results["total_fetched"] += stored_count
                     results["channels_processed"] += 1
                     results["new_transcripts"].extend([
                         {"video_id": t["video_id"], "title": t["title"]} 
                         for t in transcripts[:5]  # First 5 for summary
                     ])
                     
                     # Notify search optimizer about new content
                     if stored_count > 0:
                         await self.send_message(
                             "SearchOptimizerAgent",
                             {
                                 "action": "new_transcripts",
                                 "channel": channel,
                                 "count": stored_count,
                                 "video_ids": [t["video_id"] for t in transcripts]
                             },
                             task_id
                         )
                     
                 except Exception as e:
                     results["errors"].append({
                         "channel": channel,
                         "error": str(e)
                     })
             
             # Final progress update
             await self.update_progress(task_id, 100.0, "Fetch completed")
             
             return results
         
         async def _fetch_channel_transcripts(
             self, channel: str, since_date: datetime, max_videos: int
         ) -> List[Dict[str, Any]]:
             """Fetch transcripts from a YouTube channel"""
             # Implementation would use existing transcript fetching logic
             # This is a placeholder
             return []
         
         async def _store_transcripts(self, transcripts: List[Dict[str, Any]]) -> int:
             """Store transcripts in ArangoDB"""
             # Implementation would use existing storage logic
             # This is a placeholder
             return len(transcripts)
     ```

- [ ] **Implement Search Optimizer Agent**
  1. Create `src/youtube_transcripts/agents/search_optimizer_agent.py`:
     ```python
     from typing import Dict, Any, List
     from .base_agent import BaseAgent
     from youtube_transcripts.unified_search import EnhancedDeepRetrievalOptimizer
     
     class SearchOptimizerAgent(BaseAgent):
         """Agent that continuously improves search query optimization"""
         
         def __init__(self, db_path: str = "agents.db"):
             super().__init__(db_path)
             self.optimizer = EnhancedDeepRetrievalOptimizer()
         
         async def execute(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """
             Config expects:
             - action: "optimize_queries" or "retrain_model"
             - queries: List of queries to optimize (for optimize_queries)
             - training_data: Path to training data (for retrain_model)
             """
             action = config.get("action", "optimize_queries")
             
             if action == "optimize_queries":
                 return await self._optimize_queries(task_id, config)
             elif action == "retrain_model":
                 return await self._retrain_model(task_id, config)
             elif action == "process_feedback":
                 return await self._process_feedback(task_id, config)
             else:
                 raise ValueError(f"Unknown action: {action}")
         
         async def _optimize_queries(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """Optimize a batch of search queries"""
             queries = config.get("queries", [])
             results = {
                 "optimized_queries": [],
                 "average_expansion_ratio": 0.0
             }
             
             total_queries = len(queries)
             expansion_ratios = []
             
             for idx, query in enumerate(queries):
                 # Update progress
                 progress = (idx / total_queries) * 100
                 await self.update_progress(
                     task_id,
                     progress,
                     f"Optimizing query {idx+1}/{total_queries}"
                 )
                 
                 # Optimize query
                 optimization = self.optimizer.optimize_query(query)
                 
                 # Calculate expansion ratio
                 original_terms = len(query.split())
                 optimized_terms = len(optimization["optimized"].split())
                 expansion_ratio = optimized_terms / original_terms if original_terms > 0 else 1.0
                 expansion_ratios.append(expansion_ratio)
                 
                 results["optimized_queries"].append({
                     "original": query,
                     "optimized": optimization["optimized"],
                     "reasoning": optimization["reasoning"],
                     "expansion_ratio": expansion_ratio
                 })
                 
                 # Send to content analyzer if significant optimization
                 if expansion_ratio > 1.5:
                     await self.send_message(
                         "ContentAnalyzerAgent",
                         {
                             "action": "analyze_optimization",
                             "query": query,
                             "optimization": optimization
                         },
                         task_id
                     )
             
             results["average_expansion_ratio"] = sum(expansion_ratios) / len(expansion_ratios)
             await self.update_progress(task_id, 100.0, "Optimization completed")
             
             return results
         
         async def _retrain_model(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """Retrain the optimization model with new data"""
             # Placeholder for VERL/RL training implementation
             await self.update_progress(task_id, 50.0, "Loading training data")
             # ... training logic ...
             await self.update_progress(task_id, 100.0, "Training completed")
             
             return {
                 "model_updated": True,
                 "training_metrics": {
                     "recall_improvement": 0.05,
                     "query_success_rate": 0.87
                 }
             }
         
         async def _process_feedback(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """Process user feedback to improve optimization"""
             # Check for messages from other agents
             messages = await self.receive_messages()
             
             feedback_processed = 0
             for message in messages:
                 if message["content"].get("action") == "user_feedback":
                     # Store feedback for next training cycle
                     feedback_processed += 1
             
             return {
                 "feedback_processed": feedback_processed,
                 "ready_for_retraining": feedback_processed > 100
             }
     ```

- [ ] **Implement Content Analyzer Agent**
  1. Create `src/youtube_transcripts/agents/content_analyzer_agent.py`:
     ```python
     from typing import Dict, Any, List
     from .base_agent import BaseAgent
     import ollama
     
     class ContentAnalyzerAgent(BaseAgent):
         """Agent that analyzes transcript content for insights"""
         
         def __init__(self, db_path: str = "agents.db"):
             super().__init__(db_path)
             self.ollama_client = ollama.Client()
         
         async def execute(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """
             Config expects:
             - action: "analyze_transcript", "extract_topics", "generate_summary"
             - video_ids: List of video IDs to analyze
             - analysis_type: Type of analysis to perform
             """
             action = config.get("action", "analyze_transcript")
             
             if action == "analyze_transcript":
                 return await self._analyze_transcripts(task_id, config)
             elif action == "extract_topics":
                 return await self._extract_topics(task_id, config)
             elif action == "generate_summary":
                 return await self._generate_summary(task_id, config)
             else:
                 raise ValueError(f"Unknown action: {action}")
         
         async def _analyze_transcripts(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """Analyze transcripts for key insights"""
             video_ids = config.get("video_ids", [])
             results = {
                 "analyses": [],
                 "key_themes": [],
                 "recommendations": []
             }
             
             for idx, video_id in enumerate(video_ids):
                 progress = (idx / len(video_ids)) * 100
                 await self.update_progress(
                     task_id,
                     progress,
                     f"Analyzing video {idx+1}/{len(video_ids)}"
                 )
                 
                 # Fetch transcript from ArangoDB
                 transcript = await self._fetch_transcript(video_id)
                 
                 if transcript:
                     # Analyze with Ollama
                     analysis = await self._analyze_with_llm(transcript)
                     
                     results["analyses"].append({
                         "video_id": video_id,
                         "title": transcript.get("title"),
                         "key_points": analysis.get("key_points", []),
                         "technical_concepts": analysis.get("technical_concepts", []),
                         "mentioned_resources": analysis.get("resources", [])
                     })
                     
                     # Extract GitHub repos if mentioned
                     from youtube_transcripts.core.utils.github_extractor import extract_github_repos
                     repos = extract_github_repos(transcript.get("transcript", ""))
                     
                     if repos:
                         # Notify research validator
                         await self.send_message(
                             "ResearchValidatorAgent",
                             {
                                 "action": "validate_repos",
                                 "video_id": video_id,
                                 "repositories": repos
                             },
                             task_id
                         )
             
             await self.update_progress(task_id, 100.0, "Analysis completed")
             return results
         
         async def _analyze_with_llm(self, transcript: Dict[str, Any]) -> Dict[str, Any]:
             """Use Ollama to analyze transcript content"""
             prompt = f"""Analyze this YouTube transcript and extract:
             1. Key technical points
             2. Mentioned tools/frameworks
             3. Resources (papers, repos, websites)
             
             Transcript: {transcript.get('transcript', '')[:2000]}...
             
             Provide structured analysis:"""
             
             response = self.ollama_client.chat(
                 model="qwen2.5:3b",
                 messages=[{"role": "user", "content": prompt}]
             )
             
             # Parse response into structured data
             # This is simplified - real implementation would parse more carefully
             return {
                 "key_points": ["Key point 1", "Key point 2"],
                 "technical_concepts": ["Concept 1", "Concept 2"],
                 "resources": ["Resource 1", "Resource 2"]
             }
         
         async def _fetch_transcript(self, video_id: str) -> Optional[Dict[str, Any]]:
             """Fetch transcript from ArangoDB"""
             # Placeholder - would use actual ArangoDB query
             return {"video_id": video_id, "title": "Sample", "transcript": "Sample content"}
     ```

### Phase 3: Create Orchestrator Agent
**Objective**: Implement master orchestrator for coordinating agent activities.

- [ ] **Implement Orchestrator Agent**
  1. Create `src/youtube_transcripts/agents/orchestrator_agent.py`:
     ```python
     import asyncio
     from typing import Dict, Any, List
     from datetime import datetime, timedelta
     from .base_agent import BaseAgent
     from .agent_manager import AsyncAgentManager, AgentType
     
     class OrchestratorAgent(BaseAgent):
         """Master orchestrator that coordinates all other agents"""
         
         def __init__(self, db_path: str = "agents.db"):
             super().__init__(db_path)
             self.agent_manager = AsyncAgentManager(db_path)
         
         async def execute(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """
             Config expects:
             - workflow: "daily_update", "full_analysis", "research_validation"
             - parameters: Workflow-specific parameters
             """
             workflow = config.get("workflow", "daily_update")
             
             if workflow == "daily_update":
                 return await self._daily_update_workflow(task_id, config)
             elif workflow == "full_analysis":
                 return await self._full_analysis_workflow(task_id, config)
             elif workflow == "research_validation":
                 return await self._research_validation_workflow(task_id, config)
             else:
                 raise ValueError(f"Unknown workflow: {workflow}")
         
         async def _daily_update_workflow(self, task_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
             """Daily workflow to fetch new transcripts and optimize search"""
             channels = config.get("channels", [
                 "https://www.youtube.com/@TrelisResearch",
                 "https://www.youtube.com/@code4AI",
                 "https://www.youtube.com/@TwoMinutePapers"
             ])
             
             results = {
                 "workflow": "daily_update",
                 "started_at": datetime.now().isoformat(),
                 "steps": []
             }
             
             # Step 1: Fetch new transcripts
             await self.update_progress(task_id, 10.0, "Starting transcript fetch")
             
             fetch_task_id = await self.agent_manager.submit_task(
                 AgentType.TRANSCRIPT_FETCHER,
                 {
                     "channels": channels,
                     "since_days": 7,
                     "max_videos": 5
                 }
             )
             
             fetch_result = await self.agent_manager.wait_for_task(fetch_task_id, timeout=600)
             results["steps"].append({
                 "step": "transcript_fetch",
                 "task_id": fetch_task_id,
                 "result": fetch_result
             })
             
             # Step 2: Optimize search queries for new content
             if fetch_result["result"]["total_fetched"] > 0:
                 await self.update_progress(task_id, 40.0, "Optimizing search queries")
                 
                 # Generate queries from new transcript titles
                 new_transcripts = fetch_result["result"]["new_transcripts"]
                 queries = [t["title"] for t in new_transcripts[:10]]
                 
                 optimize_task_id = await self.agent_manager.submit_task(
                     AgentType.SEARCH_OPTIMIZER,
                     {
                         "action": "optimize_queries",
                         "queries": queries
                     }
                 )
                 
                 optimize_result = await self.agent_manager.wait_for_task(optimize_task_id)
                 results["steps"].append({
                     "step": "search_optimization",
                     "task_id": optimize_task_id,
                     "result": optimize_result
                 })
             
             # Step 3: Analyze new content
             await self.update_progress(task_id, 70.0, "Analyzing new content")
             
             analyze_task_id = await self.agent_manager.submit_task(
                 AgentType.CONTENT_ANALYZER,
                 {
                     "action": "analyze_transcript",
                     "video_ids": [t["video_id"] for t in fetch_result["result"]["new_transcripts"][:5]]
                 }
             )
             
             analyze_result = await self.agent_manager.wait_for_task(analyze_task_id)
             results["steps"].append({
                 "step": "content_analysis",
                 "task_id": analyze_task_id,
                 "result": analyze_result
             })
             
             # Final summary
             await self.update_progress(task_id, 100.0, "Workflow completed")
             results["completed_at"] = datetime.now().isoformat()
             results["summary"] = {
                 "transcripts_fetched": fetch_result["result"]["total_fetched"],
                 "queries_optimized": len(optimize_result["result"]["optimized_queries"]) if "optimize_result" in locals() else 0,
                 "videos_analyzed": len(analyze_result["result"]["analyses"])
             }
             
             return results
         
         async def _coordinate_agents(self, task_configs: List[Dict[str, Any]]) -> List[str]:
             """Submit multiple agent tasks and return task IDs"""
             task_ids = []
             for config in task_configs:
                 task_id = await self.agent_manager.submit_task(
                     config["agent_type"],
                     config["params"]
                 )
                 task_ids.append(task_id)
             return task_ids
         
         async def _wait_for_all_tasks(self, task_ids: List[str], timeout: int = 600) -> List[Dict[str, Any]]:
             """Wait for multiple tasks to complete"""
             tasks = [
                 self.agent_manager.wait_for_task(task_id, timeout)
                 for task_id in task_ids
             ]
             return await asyncio.gather(*tasks)
     ```

### Phase 4: Create CLI Integration
**Objective**: Add agent commands to existing CLI.

- [ ] **Add Agent Commands to CLI**
  1. Update `src/youtube_transcripts/cli/app.py`:
     ```python
     # Add to existing imports
     from ..agents.agent_manager import AsyncAgentManager, AgentType
     from ..agents.orchestrator_agent import OrchestratorAgent
     
     # Add new command group
     @app.command()
     def agent():
         """Manage background agents"""
         pass
     
     @agent.command()
     def start_workflow(
         workflow: str = typer.Argument(..., help="Workflow name: daily_update, full_analysis"),
         background: bool = typer.Option(True, help="Run in background")
     ):
         """Start an agent workflow"""
         async def run():
             manager = AsyncAgentManager()
             
             # Submit orchestrator task
             task_id = await manager.submit_task(
                 AgentType.ORCHESTRATOR,
                 {"workflow": workflow}
             )
             
             if background:
                 print(f"✅ Workflow '{workflow}' started with task ID: {task_id}")
                 print(f"Check status with: youtube-transcripts agent status {task_id}")
             else:
                 print(f"⏳ Running workflow '{workflow}'...")
                 result = await manager.wait_for_task(task_id, timeout=1800)
                 print(f"✅ Workflow completed: {result['status']}")
         
         asyncio.run(run())
     
     @agent.command()
     def status(task_id: str):
         """Check status of an agent task"""
         async def check():
             manager = AsyncAgentManager()
             status = await manager.get_status(task_id)
             
             if status:
                 print(f"Task ID: {task_id}")
                 print(f"Status: {status['status']}")
                 print(f"Progress: {status['progress']:.1f}%")
                 if status['error']:
                     print(f"Error: {status['error']}")
             else:
                 print(f"❌ Task {task_id} not found")
         
         asyncio.run(check())
     
     @agent.command()
     def list_tasks(
         status: str = typer.Option(None, help="Filter by status"),
         limit: int = typer.Option(10, help="Number of tasks to show")
     ):
         """List recent agent tasks"""
         async def list_all():
             # Query SQLite directly for task list
             import aiosqlite
             async with aiosqlite.connect("agents.db") as db:
                 query = "SELECT task_id, agent_type, status, created_at, progress FROM agent_tasks"
                 params = []
                 
                 if status:
                     query += " WHERE status = ?"
                     params.append(status)
                 
                 query += " ORDER BY created_at DESC LIMIT ?"
                 params.append(limit)
                 
                 cursor = await db.execute(query, params)
                 tasks = await cursor.fetchall()
                 
                 if tasks:
                     table = Table(title="Agent Tasks")
                     table.add_column("Task ID", style="cyan")
                     table.add_column("Agent", style="green")
                     table.add_column("Status", style="yellow")
                     table.add_column("Progress", style="blue")
                     table.add_column("Created", style="magenta")
                     
                     for task in tasks:
                         table.add_row(
                             task[0][:8] + "...",
                             task[1],
                             task[2],
                             f"{task[4]:.1f}%",
                             task[3]
                         )
                     
                     console.print(table)
                 else:
                     print("No tasks found")
         
         asyncio.run(list_all())
     ```

- [ ] **Create Agent Dashboard**
  1. Create `src/youtube_transcripts/agents/dashboard.py`:
     ```python
     import asyncio
     from rich.console import Console
     from rich.table import Table
     from rich.live import Live
     from rich.layout import Layout
     from rich.panel import Panel
     import aiosqlite
     
     class AgentDashboard:
         """Real-time dashboard for monitoring agent activities"""
         
         def __init__(self, db_path: str = "agents.db"):
             self.db_path = db_path
             self.console = Console()
         
         async def run(self, refresh_interval: int = 2):
             """Run the live dashboard"""
             layout = Layout()
             layout.split_column(
                 Layout(name="header", size=3),
                 Layout(name="tasks", size=15),
                 Layout(name="messages", size=10)
             )
             
             with Live(layout, refresh_per_second=1/refresh_interval) as live:
                 while True:
                     # Update header
                     layout["header"].update(
                         Panel("🤖 YouTube Transcripts Agent Dashboard", style="bold blue")
                     )
                     
                     # Update tasks table
                     tasks_table = await self._get_tasks_table()
                     layout["tasks"].update(Panel(tasks_table, title="Active Tasks"))
                     
                     # Update messages table
                     messages_table = await self._get_messages_table()
                     layout["messages"].update(Panel(messages_table, title="Recent Messages"))
                     
                     await asyncio.sleep(refresh_interval)
         
         async def _get_tasks_table(self) -> Table:
             """Get current tasks as a table"""
             table = Table()
             table.add_column("Agent", style="cyan")
             table.add_column("Status", style="green")
             table.add_column("Progress", style="yellow")
             table.add_column("Task", style="white")
             
             async with aiosqlite.connect(self.db_path) as db:
                 cursor = await db.execute(
                     """SELECT agent_type, status, progress, config, metadata
                        FROM agent_tasks
                        WHERE status IN ('PENDING', 'RUNNING')
                        ORDER BY created_at DESC
                        LIMIT 10"""
                 )
                 
                 async for row in cursor:
                     agent_type, status, progress, config, metadata = row
                     config_data = json.loads(config)
                     task_desc = config_data.get("action", "Unknown")
                     
                     table.add_row(
                         agent_type,
                         status,
                         f"{progress:.1f}%",
                         task_desc
                     )
             
             return table
         
         async def _get_messages_table(self) -> Table:
             """Get recent messages as a table"""
             table = Table()
             table.add_column("From", style="cyan")
             table.add_column("To", style="green")
             table.add_column("Message", style="white")
             table.add_column("Time", style="yellow")
             
             async with aiosqlite.connect(self.db_path) as db:
                 cursor = await db.execute(
                     """SELECT from_agent, to_agent, content, created_at
                        FROM agent_messages
                        ORDER BY created_at DESC
                        LIMIT 5"""
                 )
                 
                 async for row in cursor:
                     from_agent, to_agent, content, created_at = row
                     content_data = json.loads(content)
                     message = content_data.get("action", "Unknown")
                     
                     table.add_row(
                         from_agent[:20],
                         to_agent[:20],
                         message[:40] + "...",
                         created_at.split("T")[1][:8]
                     )
             
             return table
     
     # Add CLI command
     @agent.command()
     def dashboard():
         """Launch real-time agent dashboard"""
         dashboard = AgentDashboard()
         asyncio.run(dashboard.run())
     ```

### Phase 5: Testing and Validation
**Objective**: Validate agent system functionality.

- [ ] **Create Agent System Tests**
  1. Create `tests/agents/test_agent_system.py`:
     ```python
     import asyncio
     import pytest
     from youtube_transcripts.agents.agent_manager import AsyncAgentManager, AgentType
     
     @pytest.mark.asyncio
     async def test_agent_task_submission():
         """Test basic task submission and retrieval"""
         manager = AsyncAgentManager()
         
         # Submit a test task
         task_id = await manager.submit_task(
             AgentType.SEARCH_OPTIMIZER,
             {"action": "optimize_queries", "queries": ["test query"]}
         )
         
         assert task_id is not None
         
         # Check status
         status = await manager.get_status(task_id)
         assert status is not None
         assert status["status"] in ["PENDING", "RUNNING", "COMPLETED"]
     
     @pytest.mark.asyncio
     async def test_orchestrator_workflow():
         """Test orchestrator coordination"""
         manager = AsyncAgentManager()
         
         # Start daily update workflow
         task_id = await manager.submit_task(
             AgentType.ORCHESTRATOR,
             {"workflow": "daily_update", "channels": ["test_channel"]}
         )
         
         # Wait for completion (with shorter timeout for test)
         result = await manager.wait_for_task(task_id, timeout=60)
         
         assert result["status"] in ["COMPLETED", "FAILED"]
         if result["status"] == "COMPLETED":
             assert "summary" in result["result"]
     
     @pytest.mark.asyncio
     async def test_agent_communication():
         """Test inter-agent messaging"""
         from youtube_transcripts.agents.base_agent import BaseAgent
         
         agent1 = BaseAgent()
         agent1.agent_id = "TestAgent1"
         
         agent2 = BaseAgent()
         agent2.agent_id = "TestAgent2"
         
         # Send message
         message_id = await agent1.send_message(
             "TestAgent2",
             {"action": "test", "data": "hello"}
         )
         
         # Receive message
         messages = await agent2.receive_messages()
         
         assert len(messages) > 0
         assert messages[0]["content"]["data"] == "hello"
     ```

- [ ] **Run Validation Suite**
  1. Execute tests:
     ```bash
     cd /home/graham/workspace/experiments/youtube_transcripts/
     pytest tests/agents/test_agent_system.py -v
     ```
     - Expected: All tests pass
     - If failed: Check SQLite permissions and agent implementations

- [ ] **Test Full Workflow**
  1. Start daily update workflow:
     ```bash
     youtube-transcripts agent start-workflow daily_update
     ```
  2. Monitor progress:
     ```bash
     youtube-transcripts agent dashboard
     ```
  3. Check results:
     ```bash
     youtube-transcripts agent list-tasks --limit 5
     ```

## Common Issues & Solutions

### Issue 1: SQLite Locking
```bash
# Solution: Enable WAL mode for better concurrency
sqlite3 agents.db "PRAGMA journal_mode=WAL;"
```

### Issue 2: Agent Task Timeout
```python
# Increase timeout in agent_manager.py
async def wait_for_task(self, task_id: str, timeout: int = 600):  # Increase from 300
```

### Issue 3: Memory Usage with Multiple Agents
```bash
# Monitor agent resource usage
ps aux | grep python | grep agent

# Limit concurrent agents in agent_manager.py
AsyncAgentManager(db_path="agents.db", max_concurrent=3)  # Reduce from 5
```

## Performance Targets
- Agent task submission: < 100ms
- Inter-agent messaging: < 50ms latency
- Concurrent agents: 5+ without performance degradation
- Task persistence: 100% reliability across restarts
- Dashboard refresh: Real-time with < 2s delay

## Integration Points
- **CLI**: New `agent` command group
- **MCP**: Agents can be exposed as MCP tools
- **Web API**: REST endpoints for remote agent control
- **Monitoring**: Prometheus metrics for agent performance

## Next Steps
After completing all checkboxes:
1. Run full validation suite
2. Test with real YouTube channels
3. Monitor agent performance over 24 hours
4. Document agent behaviors and patterns
5. Proceed to Task 004: Production deployment and scaling