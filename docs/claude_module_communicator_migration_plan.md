# Claude Module Communicator MCP Migration Plan

## Executive Summary

The claude-module-communicator project currently has **0/10 compliance** with the MCP prompts standard. As the central hub orchestrating all spoke projects, it requires special treatment to enable:

1. **Discovery** of all spoke modules and their capabilities
2. **Orchestration** of cross-module workflows  
3. **Lifecycle management** of spoke modules
4. **Intelligent routing** of requests to appropriate spokes

## Current State Analysis

### Existing MCP Infrastructure
- ✅ Has MCP server implementation (`src/claude_coms/mcp/server.py`)
- ✅ Has FastAPI-based MCP server with WebSocket support
- ✅ Has tool registry and handlers
- ❌ No prompt infrastructure
- ❌ No FastMCP implementation
- ❌ No slash command integration in CLI

### Current CLI Structure
- ✅ Typer-based CLI (`src/claude_coms/cli/claude_comm.py`)
- ✅ Has slash_mcp_mixin.py but focused on generating commands, not prompts
- ✅ Comprehensive command set for module management
- ❌ No prompt-based workflows

### Module Integration
- ✅ ModuleCommunicator for inter-module messaging
- ✅ Module registry and discovery
- ✅ Event system and progress tracking
- ❌ No prompt-based orchestration

## Migration Strategy

### Phase 1: Core Infrastructure (Priority: HIGH)

1. **Copy Core Prompt Infrastructure**
   ```bash
   cp /home/graham/workspace/experiments/youtube_transcripts/src/youtube_transcripts/mcp/prompts.py \
      /home/graham/workspace/experiments/claude-module-communicator/src/claude_coms/mcp/prompts.py
   ```

2. **Create Hub-Specific Prompts** (`src/claude_coms/mcp/hub_prompts.py`)
   - Required prompts with hub-specific implementations:
     - `hub:capabilities` - List all spoke modules and their capabilities
     - `hub:help` - Context-aware help for orchestration
     - `hub:quick-start` - Guide for using the hub
   
   - Hub-specific orchestration prompts:
     - `hub:discover` - Discover all available spoke modules
     - `hub:orchestrate` - Create cross-module workflows
     - `hub:status` - Check status of all modules
     - `hub:route` - Route tasks to appropriate modules
     - `hub:workflow` - Execute predefined workflows

### Phase 2: FastMCP Migration (Priority: HIGH)

1. **Create New FastMCP Server** (`src/claude_coms/mcp/fastmcp_server.py`)
   ```python
   from fastmcp import FastMCP
   from .hub_prompts import register_all_prompts
   from .prompts import get_prompt_registry
   
   mcp = FastMCP("claude-module-communicator")
   mcp.description = "Central hub for orchestrating Granger spoke modules"
   ```

2. **Expose All Prompts as FastMCP Prompts**
   - Map internal prompts to FastMCP interface
   - Maintain compatibility with existing WebSocket server

### Phase 3: Enhanced CLI Integration (Priority: MEDIUM)

1. **Update CLI to Use Prompts**
   - Add prompt execution commands
   - Integrate with slash command system
   - Enable prompt chaining

2. **Enhance slash_mcp_mixin.py**
   - Add prompt generation alongside tool generation
   - Create hub-aware slash commands that can route to spokes

### Phase 4: Spoke Integration (Priority: HIGH)

1. **Dynamic Spoke Discovery**
   ```python
   @mcp_prompt(name="hub:discover-spokes")
   async def discover_spokes() -> str:
       """Discover all available spoke modules and their capabilities"""
       # Scan known spoke locations
       # Query each spoke's :capabilities prompt
       # Aggregate and present results
   ```

2. **Cross-Module Orchestration**
   ```python
   @mcp_prompt(name="hub:orchestrate")
   async def orchestrate_workflow(
       workflow: str,
       modules: List[str],
       parameters: Dict[str, Any]
   ) -> str:
       """Orchestrate actions across multiple spoke modules"""
       # Parse workflow definition
       # Route to appropriate spokes
       # Coordinate results
   ```

### Phase 5: Special Hub Features (Priority: MEDIUM)

1. **Module Lifecycle Management**
   - `hub:start-module` - Start a spoke module
   - `hub:stop-module` - Stop a spoke module
   - `hub:restart-module` - Restart a spoke module
   - `hub:health-check` - Check health of all modules

2. **Intelligent Routing**
   - `hub:best-module` - Find best module for a task
   - `hub:capabilities-matrix` - Show capability matrix
   - `hub:compatibility-check` - Check module compatibility

3. **Workflow Templates**
   - `hub:list-workflows` - List predefined workflows
   - `hub:create-workflow` - Create new workflow
   - `hub:run-workflow` - Execute workflow

## Implementation Steps

### Step 1: Set Up Infrastructure (Day 1)
```bash
# Create MCP prompts directory structure
mkdir -p /home/graham/workspace/experiments/claude-module-communicator/src/claude_coms/mcp/

# Copy core infrastructure
cp youtube_transcripts/src/youtube_transcripts/mcp/prompts.py \
   claude-module-communicator/src/claude_coms/mcp/prompts.py

# Create hub prompts file
touch claude-module-communicator/src/claude_coms/mcp/hub_prompts.py
```

### Step 2: Implement Required Prompts (Day 1-2)
Create the three required prompts with hub-specific logic:
- Focus on spoke discovery
- Emphasize orchestration capabilities
- Provide clear workflows

### Step 3: Add Hub-Specific Prompts (Day 2-3)
Implement orchestration prompts:
- Discovery mechanisms
- Routing logic
- Workflow execution

### Step 4: Create FastMCP Server (Day 3-4)
- New server implementation
- Expose all prompts
- Maintain backward compatibility

### Step 5: Update Configuration (Day 4)
```json
{
  "name": "claude-module-communicator",
  "version": "2.0.0",
  "description": "Central hub for Granger ecosystem with MCP prompts",
  "prompts": {
    "capabilities": {
      "description": "Discover all spoke modules and capabilities",
      "slash_command": "/hub:capabilities"
    },
    "orchestrate": {
      "description": "Orchestrate cross-module workflows",
      "slash_command": "/hub:orchestrate"
    }
  }
}
```

### Step 6: Testing (Day 5)
- Unit tests for all prompts
- Integration tests with spoke modules
- End-to-end workflow tests

## Special Considerations for Hub

1. **Spoke Registration**
   - Auto-discover spokes on startup
   - Dynamic registration of new spokes
   - Cache spoke capabilities

2. **Performance**
   - Parallel spoke queries
   - Capability caching
   - Async orchestration

3. **Error Handling**
   - Graceful degradation if spokes unavailable
   - Clear error messages
   - Fallback options

4. **Security**
   - Validate spoke responses
   - Sanitize cross-module data
   - Access control for privileged operations

## Success Metrics

1. **Compliance**: 10/10 on MCP prompts standard
2. **Discovery**: Can discover all spoke capabilities
3. **Orchestration**: Can execute cross-module workflows
4. **Performance**: < 100ms for capability discovery
5. **Reliability**: 99.9% uptime for hub operations

## Next Steps

1. Review and approve this plan
2. Begin implementation with Phase 1
3. Test each phase before proceeding
4. Document all hub-specific behaviors
5. Create tutorial for spoke integration

## Hub-Specific Prompt Examples

### hub:capabilities
```
/hub:capabilities

# Returns:
Claude Module Communicator Hub - Orchestration Center

## Connected Spokes (12 active)
- youtube_transcripts: Video transcript search and analysis
- marker: PDF to Markdown conversion
- sparta: Space cybersecurity data ingestion
- arangodb: Graph database and memory bank
...

## Orchestration Capabilities
- Cross-module workflows
- Intelligent task routing
- Module lifecycle management
```

### hub:orchestrate
```
/hub:orchestrate "Find research papers about transformers and convert to markdown"

# Orchestrates:
1. arxiv-mcp-server: Search for papers
2. marker: Convert PDFs to markdown
3. arangodb: Store in knowledge graph
```

### hub:discover
```
/hub:discover --pattern "pdf"

# Returns modules that work with PDFs:
- marker: PDF to Markdown conversion
- sparta: PDF vulnerability analysis
- darpa_crawl: PDF extraction from websites
```

This migration will transform the claude-module-communicator into a truly intelligent hub that can orchestrate the entire Granger ecosystem through natural language prompts!