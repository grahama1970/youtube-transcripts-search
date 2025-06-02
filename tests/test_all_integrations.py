#!/usr/bin/env python3
"""
Comprehensive test suite runner for YouTube Transcripts project.
Runs all tests and generates a summary report.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json


def run_pytest_on_directory(test_path, test_name):
    """Run pytest on a directory or file"""
    print(f"\n{'='*60}")
    print(f"Running {test_name}...")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # Parse pytest output for results
        passed = failed = 0
        for line in result.stdout.split('\n'):
            if 'passed' in line and 'failed' in line:
                # Parse summary line like "5 passed, 2 failed"
                parts = line.split(',')
                for part in parts:
                    if 'passed' in part:
                        passed = int(part.strip().split()[0])
                    elif 'failed' in part:
                        failed = int(part.strip().split()[0])
        
        total = passed + failed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            'name': test_name,
            'path': str(test_path),
            'success': result.returncode == 0,
            'passed': passed,
            'failed': failed,
            'total': total,
            'success_rate': success_rate,
            'output': result.stdout,
            'error': result.stderr
        }
    except Exception as e:
        return {
            'name': test_name,
            'path': str(test_path),
            'success': False,
            'passed': 0,
            'failed': 0,
            'total': 0,
            'success_rate': 0.0,
            'output': '',
            'error': str(e)
        }


def generate_summary_report(test_results):
    """Generate a summary test report"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Calculate totals
    total_passed = sum(r['passed'] for r in test_results)
    total_failed = sum(r['failed'] for r in test_results)
    total_tests = sum(r['total'] for r in test_results)
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    report = f"""# YouTube Transcripts Test Summary Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Total Tests Run**: {total_tests}  
**Overall Success Rate**: {overall_success_rate:.1f}%

## Test Results by Component

| Component | Tests | Passed | Failed | Success Rate | Status |
|-----------|-------|--------|---------|--------------|--------|
"""
    
    for result in test_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        report += f"| {result['name']} | {result['total']} | {result['passed']} | {result['failed']} | {result['success_rate']:.1f}% | {status} |\n"
    
    report += f"""

## Summary

- **Total Test Cases**: {total_tests}
- **Passed**: {total_passed} ({overall_success_rate:.1f}%)
- **Failed**: {total_failed} ({100 - overall_success_rate:.1f}%)
- **Overall Status**: {"✅ ALL TESTS PASSING" if total_failed == 0 else f"❌ {total_failed} TESTS FAILING"}

## Component Details

### Core Functionality
- Database operations: SQLite with FTS5
- YouTube API integration: Fetching and searching
- Transcript processing: Entity extraction, validation

### Search Features  
- Unified search: Local and YouTube API
- Progressive search widening: Query expansion
- Full-text search: BM25 ranking

### Advanced Features
- Agent system: Async task processing
- Scientific extractors: NLP-based metadata extraction
- MCP integration: Model Context Protocol support

## Quick Fix Guide

If tests are failing:
1. Check environment variables (YOUTUBE_API_KEY)
2. Ensure virtual environment is activated
3. Install all dependencies: `pip install -e ".[dev]"`
4. Download SpaCy models if needed: `python -m spacy download en_core_web_sm`

## Next Steps

{"🎉 All systems operational! Ready for deployment." if total_failed == 0 else "⚠️ Fix failing tests before deployment."}
"""
    
    # Print to console
    print(report)
    
    # Also save to file
    report_dir = Path("docs/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"test_summary_{timestamp}.md"
    
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"\n📊 Report saved to: {report_file}")
    
    return overall_success_rate >= 95  # Require 95% pass rate


def main():
    """Run all tests in organized structure"""
    print("🚀 Running YouTube Transcripts Test Suite")
    print("=" * 80)
    
    test_root = Path(__file__).parent
    
    # Define test groups to run
    test_groups = [
        (test_root / "core", "Core Functionality"),
        (test_root / "agents", "Agent System"),
        (test_root / "test_unified_search.py", "Unified Search"),
        (test_root / "test_search_widening.py", "Search Widening"),
        (test_root / "core/utils", "Scientific Extractors"),
    ]
    
    # Run each test group
    test_results = []
    for test_path, test_name in test_groups:
        if test_path.exists():
            result = run_pytest_on_directory(test_path, test_name)
            test_results.append(result)
            
            # Show quick summary
            if result['success']:
                print(f"✅ {test_name}: {result['passed']}/{result['total']} passed")
            else:
                print(f"❌ {test_name}: {result['failed']} failed")
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("Generating Summary Report...")
    
    success = generate_summary_report(test_results)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)