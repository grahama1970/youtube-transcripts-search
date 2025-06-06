"""
Tests for MCP Prompt Infrastructure

Tests the core prompt registry, decorators, and execution system.
"""

import pytest
import asyncio
from typing import Dict, Any

from youtube_transcripts.mcp.prompts import (
    PromptRegistry, 
    MCPPrompt,
    mcp_prompt,
    get_prompt_registry,
    format_prompt_response
)


class TestPromptRegistry:
    """Test the PromptRegistry class"""
    
    def test_registry_creation(self):
        """Test creating a new registry"""
        registry = PromptRegistry()
        assert registry is not None
        assert len(registry.list_prompts()) == 0
        assert len(registry.get_categories()) > 0
    
    def test_register_prompt(self):
        """Test registering a prompt"""
        registry = PromptRegistry()
        
        @registry.register(
            name="test:hello",
            description="Test prompt",
            category="test"
        )
        async def hello_prompt(name: str = "World") -> str:
            return f"Hello, {name}!"
        
        # Check registration
        prompts = registry.list_prompts()
        assert len(prompts) == 1
        assert prompts[0].name == "test:hello"
        assert prompts[0].description == "Test prompt"
        
        # Check category
        test_prompts = registry.list_by_category("test")
        assert len(test_prompts) == 1
    
    def test_get_prompt(self):
        """Test retrieving a prompt by name"""
        registry = PromptRegistry()
        
        @registry.register(name="test:example", description="Example")
        def example_prompt() -> str:
            return "Example"
        
        prompt = registry.get("test:example")
        assert prompt is not None
        assert prompt.name == "test:example"
        
        # Non-existent prompt
        assert registry.get("non:existent") is None
    
    @pytest.mark.asyncio
    async def test_execute_prompt(self):
        """Test executing a prompt"""
        registry = PromptRegistry()
        
        @registry.register(name="test:add", description="Add numbers")
        async def add_prompt(a: int, b: int) -> str:
            return f"Result: {a + b}"
        
        result = await registry.execute("test:add", a=5, b=3)
        assert result == "Result: 8"
    
    @pytest.mark.asyncio
    async def test_execute_with_registry_injection(self):
        """Test executing a prompt that needs registry access"""
        registry = PromptRegistry()
        
        @registry.register(name="test:count", description="Count prompts")
        async def count_prompts(registry: PromptRegistry) -> str:
            count = len(registry.list_prompts())
            return f"Total prompts: {count}"
        
        result = await registry.execute("test:count")
        assert "Total prompts: 1" in result
    
    def test_prompt_parameters_extraction(self):
        """Test automatic parameter extraction"""
        registry = PromptRegistry()
        
        @registry.register(name="test:params", description="Test params")
        def param_prompt(
            name: str,
            age: int = 18,
            active: bool = True,
            scores: list = None
        ) -> str:
            return "OK"
        
        prompt = registry.get("test:params")
        assert "name" in prompt.parameters
        assert "age" in prompt.parameters
        assert "active" in prompt.parameters
        assert "scores" in prompt.parameters
        
        # Check types
        assert prompt.parameters["name"]["type"] == "string"
        assert prompt.parameters["age"]["type"] == "integer"
        assert prompt.parameters["active"]["type"] == "boolean"
        assert prompt.parameters["scores"]["type"] == "array"
        
        # Check required
        assert "name" in prompt.required_params
        assert "age" not in prompt.required_params  # Has default


class TestMCPPromptDecorator:
    """Test the @mcp_prompt decorator"""
    
    def test_decorator_registration(self):
        """Test that decorator registers with global registry"""
        # Clear global registry first
        registry = get_prompt_registry()
        initial_count = len(registry.list_prompts())
        
        @mcp_prompt(
            name="test:decorator",
            description="Test decorator",
            category="test"
        )
        async def test_prompt() -> str:
            return "Decorated"
        
        # Check registration
        prompts = registry.list_prompts()
        assert len(prompts) > initial_count
        
        # Find our prompt
        prompt_names = [p.name for p in prompts]
        assert "test:decorator" in prompt_names
    
    def test_decorator_with_examples(self):
        """Test decorator with examples and next steps"""
        @mcp_prompt(
            name="test:example",
            description="Example prompt",
            examples=["Example 1", "Example 2"],
            next_steps=["Do this", "Then that"]
        )
        def example_prompt() -> str:
            return "Example"
        
        registry = get_prompt_registry()
        prompt = registry.get("test:example")
        
        assert len(prompt.examples) == 2
        assert "Example 1" in prompt.examples
        assert len(prompt.next_steps) == 2
        assert "Do this" in prompt.next_steps


class TestFormatPromptResponse:
    """Test the format_prompt_response helper"""
    
    def test_basic_formatting(self):
        """Test basic response formatting"""
        response = format_prompt_response(
            content="Hello, world!"
        )
        assert response == "Hello, world!"
    
    def test_formatting_with_next_steps(self):
        """Test formatting with next steps"""
        response = format_prompt_response(
            content="Main content",
            next_steps=["Step 1", "Step 2"]
        )
        
        assert "Main content" in response
        assert "## Next Steps" in response
        assert "1. Step 1" in response
        assert "2. Step 2" in response
    
    def test_formatting_with_suggestions(self):
        """Test formatting with command suggestions"""
        response = format_prompt_response(
            content="Content",
            suggestions={
                "command1": "Description 1",
                "command2": "Description 2"
            }
        )
        
        assert "Content" in response
        assert "## Quick Commands" in response
        assert "- `command1` - Description 1" in response
        assert "- `command2` - Description 2" in response
    
    def test_formatting_with_data(self):
        """Test formatting with structured data"""
        response = format_prompt_response(
            content="Results",
            data={"count": 42, "items": ["a", "b"]}
        )
        
        assert "Results" in response
        assert "## Data" in response
        assert "```json" in response
        assert '"count": 42' in response
        # Check for items array (might be pretty-printed)
        assert '"items"' in response
        assert '"a"' in response and '"b"' in response


class TestMCPPromptSchema:
    """Test MCP schema generation"""
    
    def test_prompt_to_schema(self):
        """Test converting prompt to MCP schema"""
        prompt = MCPPrompt(
            name="test:schema",
            description="Test schema",
            function=lambda x: x,
            parameters={"input": {"type": "string"}},
            required_params=["input"],
            examples=["Test example"]
        )
        
        schema = prompt.to_schema()
        
        assert schema["name"] == "test:schema"
        assert schema["description"] == "Test schema"
        assert "inputSchema" in schema
        assert schema["inputSchema"]["type"] == "object"
        assert "input" in schema["inputSchema"]["properties"]
        assert schema["inputSchema"]["required"] == ["input"]
        assert schema["examples"] == ["Test example"]
    
    def test_registry_to_schema(self):
        """Test converting entire registry to schema"""
        registry = PromptRegistry()
        
        @registry.register(name="test:one", description="One", category="test")
        def prompt_one() -> str:
            return "One"
        
        @registry.register(name="test:two", description="Two", category="test") 
        def prompt_two() -> str:
            return "Two"
        
        schema = registry.to_schema()
        
        assert "prompts" in schema
        assert len(schema["prompts"]) == 2
        assert "categories" in schema
        assert "test" in schema["categories"]
        assert len(schema["categories"]["test"]) == 2


# Integration test with real async execution
@pytest.mark.asyncio
async def test_full_prompt_workflow():
    """Test complete prompt workflow"""
    registry = PromptRegistry()
    
    # Register multiple prompts
    @registry.register(
        name="workflow:start",
        description="Start workflow",
        next_steps=["Use workflow:process next"]
    )
    async def start_workflow(task: str) -> str:
        return format_prompt_response(
            content=f"Starting workflow for: {task}",
            next_steps=["Run workflow:process"],
            suggestions={"workflow:process": "Continue processing"}
        )
    
    @registry.register(
        name="workflow:process",
        description="Process workflow"
    )
    async def process_workflow(registry: PromptRegistry) -> str:
        # Access other prompts
        prompts = registry.list_by_category("workflow")
        return f"Processing... Found {len(prompts)} workflow prompts"
    
    # Execute workflow
    result1 = await registry.execute("workflow:start", task="Testing")
    assert "Starting workflow for: Testing" in result1
    assert "workflow:process" in result1
    
    result2 = await registry.execute("workflow:process")
    assert "Processing..." in result2
    # Check that the function ran
    assert "Processing... Found" in result2


# Test error handling
@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in prompt execution"""
    registry = PromptRegistry()
    
    # Try to execute non-existent prompt
    with pytest.raises(ValueError) as exc_info:
        await registry.execute("non:existent")
    
    assert "Prompt 'non:existent' not found" in str(exc_info.value)
    
    # Register prompt that raises exception
    @registry.register(name="test:error", description="Error test")
    async def error_prompt() -> str:
        raise RuntimeError("Test error")
    
    # Execute should propagate the error
    with pytest.raises(RuntimeError) as exc_info:
        await registry.execute("test:error")
    
    assert "Test error" in str(exc_info.value)


if __name__ == "__main__":
    # Run basic validation
    print("Running MCP prompts tests...")
    
    # Test registry creation
    registry = PromptRegistry()
    assert registry is not None
    
    # Test decorator
    @mcp_prompt(name="validation:test", description="Validation test")
    async def validation_test() -> str:
        return "Validation passed"
    
    # Test execution
    result = asyncio.run(get_prompt_registry().execute("validation:test"))
    assert result == "Validation passed"
    
    print("✅ MCP prompts tests passed")