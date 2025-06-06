"""
Module: check_hub_consistency.py
Description: Functions for check hub consistency operations

External Dependencies:
- None (uses only standard library)

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

#!/usr/bin/env python3
"""
Check hub-spoke consistency across all Granger projects
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import re

def check_project_consistency(project_path: Path, project_name: str) -> Dict[str, any]:
    """Check a single project for hub integration consistency"""
    result = {
        "name": project_name,
        "path": str(project_path),
        "mcp_json": False,
        "mcp_name": None,
        "slash_commands": [],
        "cli_integration": False,
        "cli_project_name": None,
        "server_py": False,
        "server_type": None,
        "prompts": [],
        "issues": []
    }
    
    # Check mcp.json
    mcp_json_path = project_path / "mcp.json"
    if mcp_json_path.exists():
        result["mcp_json"] = True
        try:
            with open(mcp_json_path) as f:
                mcp_data = json.load(f)
                result["mcp_name"] = mcp_data.get("name")
                
                # Check prompts
                if "prompts" in mcp_data:
                    for prompt_name, prompt_data in mcp_data["prompts"].items():
                        slash_cmd = prompt_data.get("slash_command", "")
                        result["prompts"].append({
                            "name": prompt_name,
                            "slash_command": slash_cmd
                        })
                        if slash_cmd:
                            result["slash_commands"].append(slash_cmd)
                            
                # Check name consistency
                if result["mcp_name"] != project_name and result["mcp_name"] != project_name.replace("_", "-"):
                    result["issues"].append(f"MCP name '{result['mcp_name']}' doesn't match project '{project_name}'")
                            
        except Exception as e:
            result["issues"].append(f"Error reading mcp.json: {e}")
    else:
        result["issues"].append("Missing mcp.json")
    
    # Check for CLI integration
    cli_patterns = [
        project_path / "src" / project_name / "cli" / "app.py",
        project_path / "src" / project_name / "cli" / "main.py",
        project_path / "src" / project_name / "cli" / "commands.py",
        project_path / "src" / project_name / "cli.py",
        project_path / "src" / project_name.replace("-", "_") / "cli" / "app.py",
        project_path / "src" / project_name.replace("-", "_") / "cli" / "main.py",
        project_path / "src" / project_name.replace("-", "_") / "cli" / "commands.py",
        project_path / "src" / project_name.replace("-", "_") / "cli.py",
    ]
    
    for cli_path in cli_patterns:
        if cli_path.exists():
            try:
                with open(cli_path) as f:
                    content = f.read()
                    # Check for slash MCP integration
                    if "add_slash_mcp_commands" in content:
                        result["cli_integration"] = True
                        # Extract project name from call
                        match = re.search(r'add_slash_mcp_commands\([^,]+,\s*project_name\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            result["cli_project_name"] = match.group(1)
                            if result["cli_project_name"] != project_name:
                                result["issues"].append(f"CLI project_name '{result['cli_project_name']}' doesn't match '{project_name}'")
                        # For some projects, it might not have project_name param
                        elif "add_slash_mcp_commands(app" in content:
                            result["cli_integration"] = True
                        break
            except Exception as e:
                result["issues"].append(f"Error reading CLI: {e}")
    
    if not result["cli_integration"]:
        result["issues"].append("No CLI slash command integration found")
    
    # Check for server.py
    server_patterns = [
        project_path / "src" / project_name / "mcp" / "server.py",
        project_path / "src" / project_name.replace("-", "_") / "mcp" / "server.py",
        project_path / "server.py",
    ]
    
    # Special case for marker
    if project_name == "marker":
        server_patterns.append(project_path / "src" / "messages" / "mcp" / "server.py")
    
    for server_path in server_patterns:
        if server_path.exists():
            result["server_py"] = True
            try:
                with open(server_path) as f:
                    content = f.read()
                    if "FastMCP" in content:
                        result["server_type"] = "FastMCP"
                    elif "@mcp.tool" in content:
                        result["server_type"] = "Standard MCP"
                    else:
                        result["server_type"] = "Unknown"
                    break
            except Exception as e:
                result["issues"].append(f"Error reading server.py: {e}")
    
    if not result["server_py"]:
        result["issues"].append("No server.py found")
    
    # Overall status
    result["hub_ready"] = (
        result["mcp_json"] and 
        result["cli_integration"] and 
        result["server_py"] and
        len(result["issues"]) == 0
    )
    
    return result


def main():
    """Check all projects and generate consistency matrix"""
    
    # Define projects and their locations
    projects = {
        "darpa_crawl": "/home/graham/workspace/experiments/darpa_crawl",
        "gitget": "/home/graham/workspace/experiments/gitget",
        "aider-daemon": "/home/graham/workspace/experiments/aider-daemon",
        "sparta": "/home/graham/workspace/experiments/sparta",
        "marker": "/home/graham/workspace/experiments/marker",
        "arangodb": "/home/graham/workspace/experiments/arangodb",
        "youtube_transcripts": "/home/graham/workspace/experiments/youtube_transcripts",
        "claude_max_proxy": "/home/graham/workspace/experiments/claude_max_proxy",
        "arxiv-mcp-server": "/home/graham/workspace/mcp-servers/arxiv-mcp-server",
        "unsloth_wip": "/home/graham/workspace/experiments/unsloth_wip",
        "mcp-screenshot": "/home/graham/workspace/experiments/mcp-screenshot",
    }
    
    results = {}
    for project_name, project_path in projects.items():
        path = Path(project_path)
        if path.exists():
            results[project_name] = check_project_consistency(path, project_name)
        else:
            results[project_name] = {
                "name": project_name,
                "path": project_path,
                "hub_ready": False,
                "issues": ["Project directory not found"]
            }
    
    # Generate report
    print("# Hub-Spoke Consistency Matrix\n")
    print("| Project | MCP.json | Name Match | CLI Integration | Server.py | Server Type | Hub Ready | Issues |")
    print("|---------|----------|------------|-----------------|-----------|-------------|-----------|--------|")
    
    for name, result in results.items():
        mcp_status = "✅" if result.get("mcp_json") else "❌"
        name_match = "✅" if result.get("mcp_name") == name or result.get("mcp_name") == name.replace("_", "-") else "❌"
        cli_status = "✅" if result.get("cli_integration") else "❌"
        server_status = "✅" if result.get("server_py") else "❌"
        server_type = result.get("server_type", "N/A")
        hub_ready = "✅" if result.get("hub_ready") else "❌"
        issues = "; ".join(result.get("issues", [])) if result.get("issues") else "None"
        
        print(f"| {name} | {mcp_status} | {name_match} | {cli_status} | {server_status} | {server_type} | {hub_ready} | {issues} |")
    
    # Detailed slash commands
    print("\n## Slash Commands by Project\n")
    for name, result in results.items():
        if result.get("slash_commands"):
            print(f"### {name}")
            for cmd in result["slash_commands"]:
                print(f"- `{cmd}`")
            print()
    
    # Summary
    ready_count = sum(1 for r in results.values() if r.get("hub_ready"))
    total_count = len(results)
    print(f"\n## Summary\n")
    print(f"- **Hub-Ready Projects**: {ready_count}/{total_count}")
    print(f"- **Projects with Issues**: {total_count - ready_count}")
    
    # Recommendations
    print("\n## Recommendations\n")
    for name, result in results.items():
        if not result.get("hub_ready") and result.get("issues"):
            print(f"### {name}")
            for issue in result["issues"]:
                print(f"- {issue}")
            print()


if __name__ == "__main__":
    main()