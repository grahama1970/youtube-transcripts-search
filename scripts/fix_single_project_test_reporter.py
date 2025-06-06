#!/usr/bin/env python3
"""
Fix test reporting engine for a single Granger project
Safe version that handles one project at a time
"""

import os
import sys
import subprocess
from pathlib import Path

# Import the functions from the main script
sys.path.append(str(Path(__file__).parent))
from fix_all_test_reporters import (
    check_project_status,
    fix_pyproject_toml,
    create_pytest_ini,
    create_test_runner,
    install_dependencies,
    recreate_venv_with_uv
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_single_project_test_reporter.py <project_path>")
        print("Example: python fix_single_project_test_reporter.py /home/graham/workspace/experiments/marker")
        sys.exit(1)
    
    project_path = Path(sys.argv[1])
    if not project_path.exists():
        print(f"❌ Project not found: {project_path}")
        sys.exit(1)
    
    print(f"🔧 Fixing Test Reporting for: {project_path.name}")
    print("=" * 70)
    
    # Check current status
    status = check_project_status(str(project_path))
    
    # Display current status
    print(f"\n📊 Current Status:")
    if status["python_version"]:
        version_icon = "✅" if status["python_version"] == "3.10.11" else "⚠️"
        print(f"  {version_icon} Python version: {status['python_version']}")
    else:
        print(f"  ⚠️  No virtual environment found")
    
    print(f"  {'✅' if status['using_uv'] else '⚠️'} Using uv: {status['using_uv']}")
    print(f"  {'✅' if status['has_claude_test_reporter'] else '❌'} Has claude-test-reporter: {status['has_claude_test_reporter']}")
    print(f"  {'✅' if not status['pyproject_needs_update'] else '❌'} pyproject.toml configured: {not status['pyproject_needs_update']}")
    print(f"  {'✅' if not status['pytest_ini_needs_update'] else '❌'} pytest.ini configured: {not status['pytest_ini_needs_update']}")
    print(f"  {'✅' if status['has_test_runner'] else '❌'} Has test runner: {status['has_test_runner']}")
    
    # Ask for confirmation
    print(f"\n🤔 Do you want to apply fixes? (y/n): ", end="")
    response = input().strip().lower()
    
    if response != 'y':
        print("❌ Aborted.")
        sys.exit(0)
    
    print("\n📝 Applying fixes...")
    fixes_applied = []
    
    # Fix Python version if needed
    if status["needs_python_update"] or not status["venv_type"]:
        print("\n🐍 Python version needs update...")
        if recreate_venv_with_uv(project_path):
            fixes_applied.append("Recreated venv with Python 3.10.11")
            status["venv_type"] = ".venv"
    
    # Fix pyproject.toml
    if status["has_pyproject"] and status["pyproject_needs_update"]:
        print("\n📄 Updating pyproject.toml...")
        if fix_pyproject_toml(project_path):
            fixes_applied.append("Updated pyproject.toml")
    
    # Create/update pytest.ini
    if status["pytest_ini_needs_update"]:
        print("\n📄 Creating pytest.ini...")
        if create_pytest_ini(project_path):
            fixes_applied.append("Created/updated pytest.ini")
    
    # Create test runner
    if not status["has_test_runner"] and status["has_tests_dir"]:
        print("\n🏃 Creating test runner script...")
        if create_test_runner(project_path, status["name"]):
            fixes_applied.append("Created test runner script")
    
    # Install dependencies
    if status["venv_type"] and status["has_pyproject"]:
        print("\n📦 Installing dependencies...")
        if install_dependencies(project_path, status["venv_type"]):
            fixes_applied.append("Installed pytest-json-report")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ COMPLETE!")
    print("=" * 70)
    
    if fixes_applied:
        print("\n🎯 Fixes applied:")
        for fix in fixes_applied:
            print(f"   - {fix}")
        
        print("\n📝 Next steps:")
        print(f"1. cd {project_path}")
        print("2. source .venv/bin/activate")
        print("3. ./scripts/run_tests.sh")
        print("\nOr run a single test:")
        print("pytest tests/test_example.py --claude-reporter --claude-model=" + status["name"])
    else:
        print("\n✅ No fixes needed - project already configured!")
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()