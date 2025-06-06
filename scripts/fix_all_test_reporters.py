#!/usr/bin/env python3
"""
Fix test reporting engine integration across all Granger spoke projects
Ensures all projects use Python 3.10.11 with uv
"""

import os
import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python
    
# For writing TOML
import tomlkit

SPOKE_PROJECTS = [
    "/home/graham/workspace/experiments/darpa_crawl/",
    "/home/graham/workspace/experiments/gitget/",
    "/home/graham/workspace/experiments/aider-daemon/",
    "/home/graham/workspace/experiments/sparta/",
    "/home/graham/workspace/experiments/marker/",
    "/home/graham/workspace/experiments/arangodb/",
    "/home/graham/workspace/experiments/youtube_transcripts/",
    "/home/graham/workspace/experiments/claude_max_proxy/",
    "/home/graham/workspace/mcp-servers/arxiv-mcp-server/",
    "/home/graham/workspace/experiments/unsloth_wip/",
    "/home/graham/workspace/experiments/mcp-screenshot/"
]

# Pytest configuration that should be in pytest.ini
PYTEST_INI_CONTENT = """[pytest]
testpaths = tests
pythonpath = src
python_files = test_*.py *_test.py
addopts = -v --tb=short --strict-markers
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
"""

# Test runner script template
TEST_RUNNER_SCRIPT = '''#!/bin/bash
"""
Run {project_name} tests with Claude test reporter
"""

# Colors for output
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo -e "${{BLUE}}Running {project_name} Tests with Claude Test Reporter${{NC}}"
echo "============================================================"

# Ensure we're in the virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "No virtual environment found. Please create one first."
    exit 1
fi

# Default values
MODEL_NAME="{project_name}"
OUTPUT_DIR="docs/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --json)
            JSON_REPORT="--json-report --json-report-file=${{OUTPUT_DIR}}/test_report_${{TIMESTAMP}}.json"
            shift
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Run tests
echo -e "\\n${{YELLOW}}Running tests...${{NC}}"
pytest tests/ \\
    --claude-reporter \\
    --claude-model="$MODEL_NAME" \\
    --claude-output-dir="$OUTPUT_DIR" \\
    $JSON_REPORT \\
    $PYTEST_ARGS

TEST_RESULT=$?

# Summary
echo -e "\\n${{BLUE}}============================================================${{NC}}"
echo -e "${{BLUE}}Test Summary:${{NC}}"
echo -e "Tests: $([ $TEST_RESULT -eq 0 ] && echo -e "${{GREEN}}PASSED${{NC}}" || echo -e "${{YELLOW}}FAILED${{NC}}")"
echo -e "\\nReports saved to: $OUTPUT_DIR/"
echo -e "  - Claude test report: $OUTPUT_DIR/${{MODEL_NAME}}_test_report.txt"
if [[ -n "$JSON_REPORT" ]]; then
    echo -e "  - JSON report: $OUTPUT_DIR/test_report_${{TIMESTAMP}}.json"
fi
'''


def get_python_version(venv_path: Path) -> Optional[str]:
    """Get the Python version of a virtual environment"""
    python_path = venv_path / "bin" / "python"
    if not python_path.exists():
        return None
    
    try:
        result = subprocess.run(
            [str(python_path), "--version"],
            capture_output=True,
            text=True
        )
        # Parse "Python 3.10.11" -> "3.10.11"
        return result.stdout.strip().split()[-1]
    except:
        return None


def check_uv_lock(project_path: Path) -> bool:
    """Check if project has uv.lock file"""
    return (project_path / "uv.lock").exists()


def check_project_status(project_path: str) -> Dict[str, any]:
    """Check the current status of test reporting in a project"""
    project_path = Path(project_path)
    status = {
        "path": str(project_path),
        "name": project_path.name,
        "has_pyproject": False,
        "has_pytest_ini": False,
        "has_claude_test_reporter": False,
        "has_pytest_json_report": False,
        "has_test_runner": False,
        "has_tests_dir": False,
        "pyproject_needs_update": False,
        "pytest_ini_needs_update": False,
        "venv_type": None,
        "python_version": None,
        "needs_python_update": False,
        "has_uv_lock": False,
        "using_uv": False
    }
    
    # Check for pyproject.toml
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.exists():
        status["has_pyproject"] = True
        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
            
            # Check dependencies
            deps = pyproject_data.get("project", {}).get("dependencies", [])
            status["has_claude_test_reporter"] = any("claude-test-reporter" in dep for dep in deps)
            
            # Check dev dependencies
            dev_deps = pyproject_data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
            if not any("pytest-json-report" in dep for dep in dev_deps):
                status["pyproject_needs_update"] = True
                
            # Check pytest configuration
            pytest_config = pyproject_data.get("tool", {}).get("pytest", {}).get("ini_options", {})
            if "pythonpath" not in pytest_config:
                status["pyproject_needs_update"] = True
                
        except Exception as e:
            print(f"Error reading pyproject.toml: {e}")
    
    # Check for pytest.ini
    pytest_ini_path = project_path / "pytest.ini"
    if pytest_ini_path.exists():
        status["has_pytest_ini"] = True
        with open(pytest_ini_path) as f:
            content = f.read()
        if "pythonpath" not in content or "asyncio_default_fixture_loop_scope" not in content:
            status["pytest_ini_needs_update"] = True
    else:
        status["pytest_ini_needs_update"] = True
    
    # Check for test runner script
    test_runner_paths = [
        project_path / "scripts" / "run_tests.sh",
        project_path / "run_tests.sh",
        project_path / "test.sh"
    ]
    status["has_test_runner"] = any(p.exists() for p in test_runner_paths)
    
    # Check for tests directory
    status["has_tests_dir"] = (project_path / "tests").exists()
    
    # Check for virtual environment
    if (project_path / ".venv").exists():
        status["venv_type"] = ".venv"
        status["python_version"] = get_python_version(project_path / ".venv")
    elif (project_path / "venv").exists():
        status["venv_type"] = "venv"
        status["python_version"] = get_python_version(project_path / "venv")
    
    # Check if using correct Python version
    if status["python_version"] and status["python_version"] != "3.10.11":
        status["needs_python_update"] = True
    
    # Check for uv.lock
    status["has_uv_lock"] = check_uv_lock(project_path)
    status["using_uv"] = status["has_uv_lock"]
    
    return status


def fix_pyproject_toml(project_path: Path) -> bool:
    """Fix pyproject.toml to include pytest-json-report and proper pytest config"""
    pyproject_path = project_path / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"  ⚠️  No pyproject.toml found in {project_path}")
        return False
    
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        
        # Convert to tomlkit document for preserving formatting
        with open(pyproject_path, "r") as f:
            doc = tomlkit.load(f)
        
        # Ensure dev dependencies include pytest-json-report
        if "project" not in doc:
            doc["project"] = tomlkit.table()
        if "optional-dependencies" not in doc["project"]:
            doc["project"]["optional-dependencies"] = tomlkit.table()
        if "dev" not in doc["project"]["optional-dependencies"]:
            doc["project"]["optional-dependencies"]["dev"] = tomlkit.array()
        
        dev_deps = doc["project"]["optional-dependencies"]["dev"]
        
        # Add required dependencies if missing
        required_deps = [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-json-report>=1.5.0"
        ]
        
        updated = False
        for dep in required_deps:
            dep_name = dep.split(">=")[0]
            if not any(dep_name in str(existing) for existing in dev_deps):
                dev_deps.append(dep)
                print(f"  ✅ Added {dep} to dev dependencies")
                updated = True
        
        # Add pytest configuration
        if "tool" not in doc:
            doc["tool"] = tomlkit.table()
        if "pytest" not in doc["tool"]:
            doc["tool"]["pytest"] = tomlkit.table()
        if "ini_options" not in doc["tool"]["pytest"]:
            doc["tool"]["pytest"]["ini_options"] = tomlkit.table()
        
        pytest_config = doc["tool"]["pytest"]["ini_options"]
        if "pythonpath" not in pytest_config:
            pytest_config["pythonpath"] = ["src"]
            print(f"  ✅ Added pythonpath to pytest configuration")
            updated = True
        if "asyncio_mode" not in pytest_config:
            pytest_config["asyncio_mode"] = "auto"
            print(f"  ✅ Added asyncio_mode to pytest configuration")
            updated = True
        
        # Write back if updated
        if updated:
            with open(pyproject_path, "w") as f:
                f.write(tomlkit.dumps(doc))
        
        return True
    except Exception as e:
        print(f"  ❌ Error updating pyproject.toml: {e}")
        return False


def create_pytest_ini(project_path: Path) -> bool:
    """Create or update pytest.ini with proper configuration"""
    pytest_ini_path = project_path / "pytest.ini"
    
    try:
        with open(pytest_ini_path, "w") as f:
            f.write(PYTEST_INI_CONTENT)
        print(f"  ✅ Created/updated pytest.ini")
        return True
    except Exception as e:
        print(f"  ❌ Error creating pytest.ini: {e}")
        return False


def create_test_runner(project_path: Path, project_name: str) -> bool:
    """Create test runner script"""
    scripts_dir = project_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    runner_path = scripts_dir / "run_tests.sh"
    
    try:
        with open(runner_path, "w") as f:
            f.write(TEST_RUNNER_SCRIPT.format(project_name=project_name))
        
        # Make executable
        os.chmod(runner_path, 0o755)
        print(f"  ✅ Created test runner script at scripts/run_tests.sh")
        return True
    except Exception as e:
        print(f"  ❌ Error creating test runner: {e}")
        return False


def recreate_venv_with_uv(project_path: Path) -> bool:
    """Recreate virtual environment with Python 3.10.11 using uv"""
    try:
        # Check if uv is available
        result = subprocess.run(["which", "uv"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ❌ uv not found. Please install uv first.")
            return False
        
        # Backup existing venv if it exists
        venv_path = project_path / ".venv"
        backup_path = project_path / ".venv.backup"
        
        if venv_path.exists():
            print(f"  📦 Backing up existing virtual environment...")
            if backup_path.exists():
                import shutil
                shutil.rmtree(backup_path)
            venv_path.rename(backup_path)
        
        # Create new venv with Python 3.10.11
        print(f"  🔧 Creating new virtual environment with Python 3.10.11...")
        result = subprocess.run(
            ["uv", "venv", "--python=3.10.11", ".venv"],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  ❌ Failed to create venv: {result.stderr}")
            # Restore backup if creation failed
            if backup_path.exists():
                backup_path.rename(venv_path)
            return False
        
        print(f"  ✅ Created virtual environment with Python 3.10.11")
        
        # Install dependencies if pyproject.toml exists
        if (project_path / "pyproject.toml").exists():
            print(f"  📦 Installing dependencies with uv...")
            result = subprocess.run(
                ["uv", "pip", "install", "-e", ".[dev]"],
                cwd=str(project_path),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"  ✅ Dependencies installed")
            else:
                print(f"  ⚠️  Some dependencies failed to install: {result.stderr}")
        
        # Clean up backup
        if backup_path.exists():
            import shutil
            shutil.rmtree(backup_path)
            print(f"  🗑️  Removed backup")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error recreating venv: {e}")
        return False


def install_dependencies(project_path: Path, venv_type: str) -> bool:
    """Install pytest-json-report in the project's virtual environment"""
    if not venv_type:
        print(f"  ⚠️  No virtual environment found")
        return False
    
    venv_path = project_path / venv_type
    
    # Prefer uv if available
    try:
        result = subprocess.run(["which", "uv"], capture_output=True, text=True)
        if result.returncode == 0:
            # Use uv
            print(f"  📦 Installing pytest-json-report with uv...")
            subprocess.run(
                ["uv", "pip", "install", "pytest-json-report"],
                cwd=str(project_path),
                check=True
            )
            print(f"  ✅ Installed pytest-json-report with uv")
            return True
    except:
        pass
    
    # Fallback to pip
    pip_path = venv_path / "bin" / "pip"
    
    if not pip_path.exists():
        print(f"  ⚠️  pip not found in virtual environment")
        return False
    
    try:
        # Check if pytest-json-report is already installed
        result = subprocess.run(
            [str(pip_path), "list"], 
            capture_output=True, 
            text=True,
            cwd=str(project_path)
        )
        
        if "pytest-json-report" not in result.stdout:
            print(f"  📦 Installing pytest-json-report...")
            subprocess.run(
                [str(pip_path), "install", "pytest-json-report"],
                cwd=str(project_path),
                check=True
            )
            print(f"  ✅ Installed pytest-json-report")
        else:
            print(f"  ✅ pytest-json-report already installed")
        
        return True
    except Exception as e:
        print(f"  ❌ Error installing dependencies: {e}")
        return False


def main():
    """Main function to check and fix all projects"""
    print("🔧 Fixing Test Reporting Engine Across All Granger Spoke Projects")
    print("🐍 Ensuring all projects use Python 3.10.11 with uv")
    print("=" * 70)
    
    # Add dry-run mode
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("=" * 70)
    
    # Check if uv is available
    uv_check = subprocess.run(["which", "uv"], capture_output=True, text=True)
    if uv_check.returncode != 0:
        print("❌ ERROR: uv is not installed!")
        print("Please install uv first: https://github.com/astral-sh/uv")
        return
    
    results = []
    
    for project in SPOKE_PROJECTS:
        project_path = Path(project)
        if not project_path.exists():
            print(f"\n❌ Project not found: {project}")
            continue
        
        print(f"\n📁 Checking {project_path.name}...")
        status = check_project_status(project)
        
        # Display current status
        if status["python_version"]:
            version_icon = "✅" if status["python_version"] == "3.10.11" else "⚠️"
            print(f"  {version_icon} Python version: {status['python_version']}")
        else:
            print(f"  ⚠️  No virtual environment found")
        
        if status["using_uv"]:
            print(f"  ✅ Using uv (uv.lock found)")
        else:
            print(f"  ⚠️  Not using uv")
        
        fixes_applied = []
        fixes_needed = []
        
        # Check what fixes are needed
        if status["needs_python_update"] or not status["venv_type"]:
            fixes_needed.append("Recreate venv with Python 3.10.11")
        
        if status["has_pyproject"] and status["pyproject_needs_update"]:
            fixes_needed.append("Update pyproject.toml")
        
        if status["pytest_ini_needs_update"]:
            fixes_needed.append("Create/update pytest.ini")
        
        if not status["has_test_runner"] and status["has_tests_dir"]:
            fixes_needed.append("Create test runner script")
        
        if status["venv_type"] and status["has_pyproject"] and status["pyproject_needs_update"]:
            fixes_needed.append("Install pytest-json-report")
        
        # In dry-run mode, just show what would be done
        if dry_run:
            if fixes_needed:
                print(f"  🔍 Would apply fixes:")
                for fix in fixes_needed:
                    print(f"     - {fix}")
            fixes_applied = []  # Don't actually apply
        else:
            # Apply fixes
            if status["needs_python_update"] or not status["venv_type"]:
                if recreate_venv_with_uv(project_path):
                    fixes_applied.append("Recreated venv with Python 3.10.11")
                    status["venv_type"] = ".venv"
                    status["python_version"] = "3.10.11"
                    status["needs_python_update"] = False
            
            if status["has_pyproject"] and status["pyproject_needs_update"]:
                if fix_pyproject_toml(project_path):
                    fixes_applied.append("Updated pyproject.toml")
            
            if status["pytest_ini_needs_update"]:
                if create_pytest_ini(project_path):
                    fixes_applied.append("Created/updated pytest.ini")
            
            if not status["has_test_runner"] and status["has_tests_dir"]:
                if create_test_runner(project_path, status["name"]):
                    fixes_applied.append("Created test runner script")
            
            if status["venv_type"] and status["has_pyproject"]:
                if install_dependencies(project_path, status["venv_type"]):
                    fixes_applied.append("Installed pytest-json-report")
        
        # Summary for this project
        if fixes_applied:
            print(f"  🎯 Fixes applied: {', '.join(fixes_applied)}")
        else:
            if (status["has_claude_test_reporter"] and 
                not status["pyproject_needs_update"] and 
                status["python_version"] == "3.10.11"):
                print(f"  ✅ Project already properly configured")
            else:
                print(f"  ⚠️  No fixes applied (may need manual intervention)")
        
        results.append({
            "project": status["name"],
            "status": status,
            "fixes": fixes_applied,
            "fixes_needed": fixes_needed if dry_run else []
        })
    
    # Generate summary report
    print("\n" + "=" * 70)
    print("📊 SUMMARY REPORT")
    print("=" * 70)
    
    for result in results:
        status = result["status"]
        all_good = (result["fixes"] or 
                   (status["has_claude_test_reporter"] and 
                    not status["pyproject_needs_update"] and
                    status["python_version"] == "3.10.11"))
        
        status_icon = "✅" if all_good else "⚠️"
        print(f"\n{status_icon} {result['project']}:")
        
        # Show Python version
        if status["python_version"]:
            py_icon = "✅" if status["python_version"] == "3.10.11" else "❌"
            print(f"   {py_icon} Python: {status['python_version']}")
        else:
            print(f"   ❌ Python: No venv")
        
        # Show uv status
        uv_icon = "✅" if status["using_uv"] else "❌"
        print(f"   {uv_icon} Using uv: {status['using_uv']}")
        
        # Show fixes
        if result["fixes"]:
            print("   📝 Fixes applied:")
            for fix in result["fixes"]:
                print(f"      - {fix}")
        elif status["has_claude_test_reporter"] and status["python_version"] == "3.10.11":
            print("   ✅ Already properly configured")
        else:
            print("   ⚠️  Needs manual configuration")
    
    # Save detailed report
    report_path = Path("/home/graham/workspace/experiments/youtube_transcripts/docs/reports/granger_test_reporter_fix_report.json")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    print("\n✅ Test reporter fix process complete!")


if __name__ == "__main__":
    main()