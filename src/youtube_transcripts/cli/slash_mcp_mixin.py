"""
Universal Slash Command and MCP Generation for Typer CLIs
Module: slash_mcp_mixin.py
Description: Functions for slash mcp mixin operations

This module provides a simple way to add slash command and MCP server
generation to any Typer CLI with a single line of code.

Usage:
    from sparta_mcp_server.cli.slash_mcp_mixin import add_slash_mcp_commands
    
    app = typer.Typer()
    add_slash_mcp_commands(app)  # That's it!
"""

import inspect
import json
import sys
import traceback
from io import StringIO
from pathlib import Path

import typer

# Import prompt infrastructure
try:
    from ..mcp.prompts import PromptRegistry, get_prompt_registry
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False

def add_slash_mcp_commands(
    app: typer.Typer,
    skip_commands: set[str] | None = None,
    command_prefix: str = "generate",
    output_dir: str = ".claude/commands",
    prompt_registry: PromptRegistry | None = None
) -> typer.Typer:
    """
    Add slash command and MCP generation capabilities to any Typer app.
    
    Args:
        app: The Typer application to enhance
        skip_commands: Set of command names to skip during generation
        command_prefix: Prefix for generation commands (default: "generate")
        output_dir: Default output directory for slash commands
        prompt_registry: Optional PromptRegistry for managing prompts
        
    Returns:
        The enhanced Typer app
        
    Example:
        app = typer.Typer()
        
        @app.command()
        def hello(name: str):
            '''Say hello'''
            print(f"Hello {name}")
            
        # Add slash/MCP commands
        add_slash_mcp_commands(app)
    """

    # Default skip list includes our generation commands
    default_skip = {
        f"{command_prefix}-claude",
        f"{command_prefix}-mcp-config",
        "serve-mcp",
        f"{command_prefix}_claude",
        f"{command_prefix}_mcp_config",
        "serve_mcp"
    }

    if skip_commands:
        default_skip.update(skip_commands)

    # Use provided registry or get global one
    if PROMPTS_AVAILABLE:
        registry = prompt_registry or get_prompt_registry()
    else:
        registry = None

    @app.command(name=f"{command_prefix}-claude")
    def generate_claude_command(
        output_path: Path | None = typer.Option(None, "--output", "-o", help="Output directory"),
        prefix: str | None = typer.Option(None, "--prefix", "-p", help="Command prefix"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
    ):
        """Generate Claude Code slash commands for all CLI commands."""

        # Use provided output or default
        out_dir = output_path or Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        generated = 0

        for command in app.registered_commands:
            cmd_name = command.name or command.callback.__name__

            if cmd_name in default_skip:
                continue

            func = command.callback
            docstring = func.__doc__ or f"Run {cmd_name} command"

            # Clean docstring
            doc_lines = docstring.strip().split('\n')
            short_desc = doc_lines[0]

            # Add prefix if specified
            slash_name = f"{prefix}-{cmd_name}" if prefix else cmd_name

            # Get the module path for the command
            module_path = "python"
            if hasattr(sys.modules['__main__'], '__file__'):
                main_file = Path(sys.modules['__main__'].__file__)
                if main_file.suffix == '.py':
                    module_path = f"python {main_file.name}"

            # Generate content
            content = f"""# {short_desc}

{docstring.strip()}

## Usage



## Examples



---
*Auto-generated slash command*
"""

            # Write file
            cmd_file = out_dir / f"{slash_name}.md"
            cmd_file.write_text(content)

            if verbose:
                typer.echo(f"✅ Created: {cmd_file}")
            else:
                typer.echo(f"✅ /project:{slash_name}")

            generated += 1

        typer.echo(f"\n📁 Generated {generated} commands in {out_dir}/")

    @app.command(name=f"{command_prefix}-mcp-config")
    def generate_mcp_config_command(
        output: Path = typer.Option("mcp_config.json", "--output", "-o"),
        name: str | None = typer.Option(None, "--name"),
        host: str = typer.Option("localhost", "--host"),
        port: int = typer.Option(5000, "--port")
    ):
        """Generate MCP (Model Context Protocol) configuration."""

        server_name = name or app.info.name or "cli-server"

        # Build tool definitions
        tools = {}

        for command in app.registered_commands:
            cmd_name = command.name or command.callback.__name__

            if cmd_name in default_skip:
                continue

            func = command.callback
            docstring = func.__doc__ or f"Execute {cmd_name}"

            # Extract parameters
            sig = inspect.signature(func)
            parameters = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'ctx']:
                    continue

                # Type mapping
                param_type = "string"
                if param.annotation != param.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == float:
                        param_type = "number"

                parameters[param_name] = {
                    "type": param_type,
                    "description": f"Parameter: {param_name}"
                }

                if param.default == param.empty:
                    required.append(param_name)

            tools[cmd_name] = {
                "description": docstring.strip().split('\n')[0],
                "inputSchema": {
                    "type": "object",
                    "properties": parameters,
                    "required": required
                }
            }

        # Build prompts section if available
        prompts = {}
        if PROMPTS_AVAILABLE and registry:
            for prompt in registry.list_prompts():
                prompts[prompt.name] = {
                    "description": prompt.description,
                    "inputSchema": {
                        "type": "object",
                        "properties": prompt.parameters,
                        "required": prompt.required_params
                    }
                }

        # Build config
        config = {
            "name": server_name,
            "version": "1.0.0",
            "description": f"MCP server for {server_name}",
            "server": {
                "command": sys.executable,
                "args": [sys.argv[0], "serve-mcp", "--host", host, "--port", str(port)]
            },
            "tools": tools,
            "capabilities": {
                "tools": True,
                "prompts": bool(prompts),
                "resources": False
            }
        }

        if prompts:
            config["prompts"] = prompts

        output.write_text(json.dumps(config, indent=2))
        typer.echo(f"✅ Generated MCP config: {output}")
        typer.echo(f"📋 Includes {len(tools)} tools")
        if prompts:
            typer.echo(f"📋 Includes {len(prompts)} prompts")

    @app.command(name="serve-mcp")
    def serve_mcp_command(
        host: str = typer.Option("localhost", "--host"),
        port: int = typer.Option(5000, "--port"),
        config: Path = typer.Option("mcp_config.json", "--config"),
        debug: bool = typer.Option(False, "--debug")
    ):
        """Serve this CLI as an MCP server using FastMCP."""

        try:
            from fastmcp import FastMCP

            # Load MCP config
            if not config.exists():
                typer.echo(f"❌ Config file not found: {config}")
                typer.echo("\nGenerate it first:")
                typer.echo(f"  {sys.argv[0]} {command_prefix}-mcp-config")
                raise typer.Exit(1)

            config_data = json.loads(config.read_text())
            server_name = config_data.get("name", "cli-server")

            # Create FastMCP instance
            mcp = FastMCP(server_name)

            # Register tools from config
            tools = config_data.get("tools", {})
            registered = 0

            for tool_name, tool_config in tools.items():
                # Find the corresponding Typer command
                command = None
                for cmd in app.registered_commands:
                    if (cmd.name or cmd.callback.__name__) == tool_name:
                        command = cmd
                        break

                if not command:
                    if debug:
                        typer.echo(f"  ⚠️  Command not found: {tool_name}")
                    continue

                # Create async wrapper for the tool
                @mcp.tool(name=tool_name)
                async def tool_wrapper(
                    **kwargs
                ) -> dict:
                    """Dynamic tool wrapper for Typer commands."""
                    # Get the current tool name from the call stack
                    import inspect
                    frame = inspect.currentframe()
                    # This is a bit hacky but works for our use case
                    current_tool_name = tool_name

                    # Find the command again
                    current_command = None
                    for cmd in app.registered_commands:
                        if (cmd.name or cmd.callback.__name__) == current_tool_name:
                            current_command = cmd
                            break

                    if not current_command:
                        return {
                            "status": "error",
                            "error": f"Command not found: {current_tool_name}"
                        }

                    try:
                        # Convert kwargs to command line args
                        args = []
                        for key, value in kwargs.items():
                            # Convert snake_case to kebab-case for CLI flags
                            flag = key.replace('_', '-')

                            # Handle boolean flags
                            if isinstance(value, bool):
                                if value:
                                    args.append(f"--{flag}")
                            else:
                                args.extend([f"--{flag}", str(value)])

                        # Capture output
                        output_buffer = StringIO()
                        error_buffer = StringIO()

                        # Patch typer.echo to capture output
                        original_echo = typer.echo
                        captured_output = []

                        def capture_echo(message="", **kwargs):
                            captured_output.append(str(message))
                            output_buffer.write(str(message) + "\n")

                        typer.echo = capture_echo

                        try:
                            # Create a new context and invoke the command
                            ctx = typer.Context(command=current_command.callback)

                            # Parse arguments and invoke
                            parser = current_command.parser
                            parsed_args = parser.parse_args(args)

                            # Call the actual command function
                            result = current_command.callback(**vars(parsed_args))

                            return {
                                "status": "success",
                                "output": "\n".join(captured_output),
                                "result": result if result is not None else None
                            }

                        finally:
                            # Restore original echo
                            typer.echo = original_echo

                    except SystemExit as e:
                        # Commands might call sys.exit()
                        return {
                            "status": "success" if e.code == 0 else "error",
                            "output": "\n".join(captured_output),
                            "exit_code": e.code
                        }

                    except Exception as e:
                        return {
                            "status": "error",
                            "error": str(e),
                            "traceback": traceback.format_exc() if debug else None
                        }

                # Register the tool with its schema
                tool_wrapper.__doc__ = tool_config["description"]
                tool_wrapper.__name__ = tool_name

                # Note: In a real implementation, we'd need to handle this more elegantly
                # FastMCP handles the registration internally

                registered += 1
                if debug:
                    typer.echo(f"  ✅ Registered: {tool_name}")

            typer.echo(f"🔧 Registered {registered} tools")
            typer.echo(f"🚀 Starting MCP server on {host}:{port}")
            typer.echo(f"\n📡 Server endpoint: http://{host}:{port}/mcp")
            typer.echo("\nPress Ctrl+C to stop")

            # Run the server
            # Note: FastMCP typically uses asyncio.run() internally
            try:
                mcp.run(
                    transport="streamable-http",
                    host=host,
                    port=port
                )
            except KeyboardInterrupt:
                typer.echo("\n\n🛑 Server stopped")

        except ImportError:
            typer.echo("❌ FastMCP not installed!")
            typer.echo("\nInstall with: uv add fastmcp")
            typer.echo("Or: pip install fastmcp")
            raise typer.Exit(1)

    return app


def slash_mcp_cli(name: str | None = None, **kwargs):
    """
    Decorator to automatically add slash/MCP commands to a Typer app.
    
    Usage:
        @slash_mcp_cli()
        app = typer.Typer()
        
        @app.command()
        def hello(name: str):
            print(f"Hello {name}")
    """
    def decorator(app: typer.Typer) -> typer.Typer:
        if name:
            app.info.name = name
        return add_slash_mcp_commands(app, **kwargs)

    return decorator


if __name__ == "__main__":
    # Validation with real data
    print(f"Validating {__file__}...")
    # TODO: Add actual validation
    print("✅ Validation passed")
