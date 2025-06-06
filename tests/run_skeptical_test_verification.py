#!/usr/bin/env python3
"""
Skeptical Test Verification Engine for YouTube Transcripts
Following TASK_LIST_TEMPLATE_GUIDE_V2.md compliance framework

This script runs all tests with skeptical verification and confidence scoring.
"""

import subprocess
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re

class SkepticalTestVerifier:
    """Skeptical test verification engine with confidence scoring"""
    
    def __init__(self, max_verification_loops: int = 3, confidence_threshold: float = 0.9):
        self.max_loops = max_verification_loops
        self.confidence_threshold = confidence_threshold
        self.test_results = {}
        self.verification_log = []
        
    def run_test_suite(self, test_path: str) -> Dict:
        """Run a test suite and capture detailed results"""
        print(f"\n{'='*60}")
        print(f"Running test suite: {test_path}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Run pytest with JSON output
        cmd = [
            "python", "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=/tmp/test_report.json",
            "--no-header",
            "-q"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="/home/graham/workspace/experiments/youtube_transcripts"
        )
        
        duration = time.time() - start_time
        
        # Parse results
        test_output = {
            "path": test_path,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to load JSON report
        try:
            with open("/tmp/test_report.json", "r") as f:
                json_report = json.load(f)
                test_output["json_report"] = json_report
        except:
            test_output["json_report"] = None
            
        return test_output
    
    def calculate_confidence(self, test_result: Dict, verification_loop: int) -> float:
        """Calculate confidence score for test results"""
        confidence = 0.0
        
        # Base confidence from test result
        if test_result["return_code"] == 0:
            confidence = 0.5  # Base confidence for passing tests
        else:
            confidence = 0.2  # Lower base for failing tests
            
        # Check for flakiness indicators
        stdout = test_result.get("stdout", "")
        stderr = test_result.get("stderr", "")
        
        # Positive indicators
        if "passed" in stdout.lower():
            confidence += 0.1
        if "failed=0" in stdout:
            confidence += 0.2
        if test_result.get("json_report") and test_result["json_report"].get("summary", {}).get("failed", 1) == 0:
            confidence += 0.2
            
        # Negative indicators
        if "timeout" in stderr.lower() or "timeout" in stdout.lower():
            confidence -= 0.3
        if "segmentation fault" in stderr.lower():
            confidence -= 0.5
        if "connection error" in stderr.lower() or "connection error" in stdout.lower():
            confidence -= 0.2
            
        # Adjust for verification loop
        if verification_loop > 1:
            confidence += 0.1 * (verification_loop - 1)  # Increase confidence with consistent results
            
        return min(max(confidence, 0.0), 1.0)
    
    def verify_test_suite(self, test_path: str) -> Dict:
        """Run test suite with verification loops"""
        suite_results = {
            "test_path": test_path,
            "verification_loops": [],
            "final_confidence": 0.0,
            "final_status": "UNKNOWN",
            "issues": []
        }
        
        previous_results = []
        
        for loop in range(1, self.max_loops + 1):
            print(f"\nVerification loop {loop}/{self.max_loops} for {test_path}")
            
            # Run the test
            result = self.run_test_suite(test_path)
            confidence = self.calculate_confidence(result, loop)
            
            verification = {
                "loop": loop,
                "confidence": confidence,
                "passed": result["return_code"] == 0,
                "duration": result["duration"],
                "summary": self.extract_test_summary(result)
            }
            
            suite_results["verification_loops"].append(verification)
            previous_results.append(result["return_code"] == 0)
            
            # Check for consistency
            if len(set(previous_results)) > 1:
                suite_results["issues"].append("INCONSISTENT_RESULTS")
                confidence *= 0.7  # Reduce confidence for inconsistent results
                
            # Check if we've reached confidence threshold
            if confidence >= self.confidence_threshold:
                suite_results["final_confidence"] = confidence
                suite_results["final_status"] = "PASS" if result["return_code"] == 0 else "FAIL"
                print(f"✓ Reached confidence threshold: {confidence:.2f}")
                break
                
            # Early termination for consistent failures
            if loop > 1 and all(not r for r in previous_results):
                suite_results["final_confidence"] = confidence
                suite_results["final_status"] = "FAIL"
                suite_results["issues"].append("CONSISTENT_FAILURE")
                print(f"✗ Consistent failures detected")
                break
                
        # Final assessment
        if suite_results["final_status"] == "UNKNOWN":
            suite_results["final_confidence"] = confidence
            suite_results["final_status"] = "UNCERTAIN"
            suite_results["issues"].append("LOW_CONFIDENCE")
            
        return suite_results
    
    def extract_test_summary(self, test_result: Dict) -> Dict:
        """Extract test summary from results"""
        summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        # Try to extract from JSON report first
        if test_result.get("json_report"):
            json_summary = test_result["json_report"].get("summary", {})
            summary.update({
                "total": json_summary.get("total", 0),
                "passed": json_summary.get("passed", 0),
                "failed": json_summary.get("failed", 0),
                "skipped": json_summary.get("skipped", 0),
                "errors": json_summary.get("error", 0)
            })
        else:
            # Parse from stdout
            stdout = test_result.get("stdout", "")
            
            # Look for pytest summary line
            summary_match = re.search(r'(\d+) passed', stdout)
            if summary_match:
                summary["passed"] = int(summary_match.group(1))
                
            failed_match = re.search(r'(\d+) failed', stdout)
            if failed_match:
                summary["failed"] = int(failed_match.group(1))
                
            skipped_match = re.search(r'(\d+) skipped', stdout)
            if skipped_match:
                summary["skipped"] = int(skipped_match.group(1))
                
            summary["total"] = summary["passed"] + summary["failed"] + summary["skipped"]
            
        return summary
    
    def run_all_tests(self) -> Dict:
        """Run all test suites with verification"""
        test_suites = [
            "tests/core/test_database.py",
            "tests/core/test_youtube.py",
            "tests/core/utils/test_scientific_extractors.py",
            "tests/integration/test_arangodb_features.py",
            "tests/integration/test_arxiv_youtube_integration.py",
            "tests/integration/test_database_adapter.py",
            "tests/mcp/test_prompts.py",
            "tests/agents/test_agents.py",
            "tests/level_0/test_youtube_transcripts_standardized.py",
            "tests/scenarios/test_level0_scenarios.py",
            "tests/test_search_widening.py",
            "tests/test_unified_search.py",
            "tests/test_arangodb_connection.py",
            "tests/test_integration_summary.py"
        ]
        
        all_results = {
            "start_time": datetime.now().isoformat(),
            "test_suites": {},
            "summary": {
                "total_suites": len(test_suites),
                "passed_suites": 0,
                "failed_suites": 0,
                "uncertain_suites": 0,
                "total_confidence": 0.0
            }
        }
        
        for test_suite in test_suites:
            print(f"\n{'#'*80}")
            print(f"# Verifying: {test_suite}")
            print(f"{'#'*80}")
            
            try:
                result = self.verify_test_suite(test_suite)
                all_results["test_suites"][test_suite] = result
                
                # Update summary
                if result["final_status"] == "PASS":
                    all_results["summary"]["passed_suites"] += 1
                elif result["final_status"] == "FAIL":
                    all_results["summary"]["failed_suites"] += 1
                else:
                    all_results["summary"]["uncertain_suites"] += 1
                    
                all_results["summary"]["total_confidence"] += result["final_confidence"]
                
            except Exception as e:
                print(f"ERROR verifying {test_suite}: {e}")
                all_results["test_suites"][test_suite] = {
                    "error": str(e),
                    "final_status": "ERROR",
                    "final_confidence": 0.0
                }
                all_results["summary"]["failed_suites"] += 1
                
        # Calculate average confidence
        all_results["summary"]["average_confidence"] = (
            all_results["summary"]["total_confidence"] / len(test_suites)
        )
        
        all_results["end_time"] = datetime.now().isoformat()
        
        return all_results
    
    def generate_report(self, results: Dict) -> str:
        """Generate comprehensive verification report"""
        report = []
        report.append("# Skeptical Test Verification Report")
        report.append(f"Generated: {results['end_time']}")
        report.append(f"Confidence Threshold: {self.confidence_threshold}")
        report.append(f"Max Verification Loops: {self.max_loops}")
        report.append("")
        
        # Summary
        summary = results["summary"]
        report.append("## Summary")
        report.append(f"- Total Test Suites: {summary['total_suites']}")
        report.append(f"- Passed: {summary['passed_suites']} ✅")
        report.append(f"- Failed: {summary['failed_suites']} ❌")
        report.append(f"- Uncertain: {summary['uncertain_suites']} ⚠️")
        report.append(f"- Average Confidence: {summary['average_confidence']:.2%}")
        report.append("")
        
        # Detailed Results
        report.append("## Detailed Results")
        report.append("")
        report.append("| Test Suite | Status | Confidence | Loops | Issues |")
        report.append("|------------|--------|------------|-------|--------|")
        
        for suite, result in results["test_suites"].items():
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌",
                "UNCERTAIN": "⚠️",
                "ERROR": "🔥"
            }.get(result.get("final_status", "ERROR"), "❓")
            
            confidence = result.get("final_confidence", 0.0)
            loops = len(result.get("verification_loops", []))
            issues = ", ".join(result.get("issues", [])) or "None"
            
            report.append(f"| {suite} | {status_icon} {result.get('final_status', 'ERROR')} | {confidence:.2%} | {loops} | {issues} |")
            
        report.append("")
        
        # Issues requiring attention
        report.append("## Issues Requiring Attention")
        report.append("")
        
        critical_issues = []
        for suite, result in results["test_suites"].items():
            if result.get("final_status") in ["FAIL", "UNCERTAIN", "ERROR"]:
                critical_issues.append(f"- **{suite}**: {result.get('final_status')} (Confidence: {result.get('final_confidence', 0):.2%})")
                if result.get("issues"):
                    for issue in result["issues"]:
                        critical_issues.append(f"  - {issue}")
                        
        if critical_issues:
            report.extend(critical_issues)
        else:
            report.append("No critical issues found! All tests passed with high confidence.")
            
        return "\n".join(report)


def main():
    """Main execution function"""
    print("Starting Skeptical Test Verification Engine")
    print("="*80)
    
    # Create verifier instance
    verifier = SkepticalTestVerifier(max_verification_loops=3, confidence_threshold=0.9)
    
    # Run all tests
    results = verifier.run_all_tests()
    
    # Generate report
    report = verifier.generate_report(results)
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"/home/graham/workspace/experiments/youtube_transcripts/docs/reports/skeptical_verification_{timestamp}.md"
    
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
        
    # Also save JSON results
    json_path = f"/home/graham/workspace/experiments/youtube_transcripts/test_reports/skeptical_verification_{timestamp}.json"
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
        
    # Print summary
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    print(f"Report saved to: {report_path}")
    print(f"JSON results saved to: {json_path}")
    print("")
    print("Summary:")
    print(f"- Passed: {results['summary']['passed_suites']}/{results['summary']['total_suites']}")
    print(f"- Failed: {results['summary']['failed_suites']}/{results['summary']['total_suites']}")
    print(f"- Uncertain: {results['summary']['uncertain_suites']}/{results['summary']['total_suites']}")
    print(f"- Average Confidence: {results['summary']['average_confidence']:.2%}")
    
    # Exit with appropriate code
    if results['summary']['failed_suites'] > 0 or results['summary']['uncertain_suites'] > 0:
        print("\n⚠️  Some tests failed or had low confidence!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed with high confidence!")
        sys.exit(0)


if __name__ == "__main__":
    main()