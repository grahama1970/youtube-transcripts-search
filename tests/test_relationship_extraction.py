#!/usr/bin/env python3
"""
Non-mocked tests for relationship extraction functionality.
Tests with real transcript pairs and validates actual relationship discovery.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from src.youtube_transcripts.unified_search import GraphMemoryIntegration, UnifiedSearchConfig


class TestRelationshipExtraction:
    """Test relationship extraction between transcripts"""
    
    @classmethod
    def setup_class(cls):
        cls.results = []
        cls.test_transcript_pairs = [
            {
                "id": "same_channel_pair",
                "transcript1": {
                    "video_id": "test_001",
                    "title": "Introduction to Reinforcement Learning",
                    "channel_name": "TrelisResearch",
                    "published_at": "2025-05-01T10:00:00Z",
                    "content": """
                        Today we explore reinforcement learning fundamentals. OpenAI has pioneered
                        many advances in this field. The PPO algorithm is particularly important.
                        Q-learning forms the foundation of many modern approaches.
                    """
                },
                "transcript2": {
                    "video_id": "test_002",
                    "title": "Advanced RL Techniques with PPO",
                    "channel_name": "TrelisResearch",
                    "published_at": "2025-05-03T10:00:00Z",
                    "content": """
                        Building on our previous video about reinforcement learning, today we dive
                        deep into PPO (Proximal Policy Optimization). OpenAI used this technique
                        in many of their breakthrough projects. The algorithm improves upon
                        standard policy gradient methods.
                    """
                },
                "expected_relationships": ["SAME_CHANNEL", "SHARES_ENTITY", "PUBLISHED_NEAR", "SIMILAR_TOPIC"]
            },
            {
                "id": "different_channel_pair",
                "transcript1": {
                    "video_id": "test_003",
                    "title": "Monte Carlo Tree Search Explained",
                    "channel_name": "DiscoverAI",
                    "published_at": "2025-04-15T10:00:00Z",
                    "content": """
                        Monte Carlo Tree Search (MCTS) revolutionized game AI. DeepMind's AlphaGo
                        famously used MCTS combined with neural networks. The algorithm balances
                        exploration and exploitation effectively.
                    """
                },
                "transcript2": {
                    "video_id": "test_004",
                    "title": "DeepMind's Game AI Breakthroughs",
                    "channel_name": "AIResearchHub",
                    "published_at": "2025-05-20T10:00:00Z",
                    "content": """
                        DeepMind has achieved remarkable results in game AI. Their use of
                        neural networks and search algorithms like MCTS has been groundbreaking.
                        AlphaGo and AlphaZero demonstrate the power of these approaches.
                    """
                },
                "expected_relationships": ["SHARES_ENTITY", "SIMILAR_TOPIC"]
            }
        ]
    
    @classmethod
    def teardown_class(cls):
        """Generate report after all tests"""
        cls.generate_report(cls)
    
    def test_extract_relationships_basic(self):
        """Test basic relationship extraction between transcript pairs"""
        print("\n🔗 Testing Basic Relationship Extraction...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Basic Relationship Extraction",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        success_count = 0
        
        for test_case in self.test_transcript_pairs:
            start_time = datetime.now()
            
            try:
                # Extract relationships
                relationships = graph_memory.extract_relationships_between_transcripts(
                    test_case["transcript1"],
                    test_case["transcript2"]
                )
                
                # Categorize found relationships
                found_types = {rel["type"] for rel in relationships}
                expected_types = set(test_case["expected_relationships"])
                
                # Calculate metrics
                matched_types = found_types & expected_types
                precision = len(matched_types) / len(found_types) if found_types else 0
                recall = len(matched_types) / len(expected_types) if expected_types else 0
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                # Test passes if we find at least 50% of expected relationships
                test_passed = recall >= 0.5
                if test_passed:
                    success_count += 1
                
                duration = (datetime.now() - start_time).total_seconds()
                
                # Extract relationship details
                rel_details = {}
                for rel in relationships:
                    rel_type = rel["type"]
                    if rel_type not in rel_details:
                        rel_details[rel_type] = []
                    rel_details[rel_type].append(rel.get("properties", {}))
                
                self.results.append({
                    "test_name": f"Relationship Extraction - {test_case['id']}",
                    "status": "PASS" if test_passed else "FAIL",
                    "total_relationships": len(relationships),
                    "found_types": list(found_types),
                    "expected_types": list(expected_types),
                    "matched_types": list(matched_types),
                    "precision": f"{precision:.1%}",
                    "recall": f"{recall:.1%}",
                    "f1_score": f"{f1_score:.2f}",
                    "duration": f"{duration:.3f}s",
                    "relationship_details": rel_details
                })
                
            except Exception as e:
                self.results.append({
                    "test_name": f"Relationship Extraction - {test_case['id']}",
                    "status": "ERROR",
                    "error": str(e),
                    "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
                })
        
        assert success_count == len(self.test_transcript_pairs), f"Only {success_count}/{len(self.test_transcript_pairs)} tests passed"
    
    def test_temporal_relationships(self):
        """Test temporal relationship detection"""
        print("\n📅 Testing Temporal Relationships...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Temporal Relationships",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        # Test cases with different time gaps
        test_cases = [
            {
                "name": "within_week",
                "transcript1": {
                    "video_id": "temporal_001",
                    "title": "Part 1: Introduction",
                    "channel_name": "TestChannel",
                    "published_at": "2025-05-01T10:00:00Z",
                    "content": "Introduction to the series"
                },
                "transcript2": {
                    "video_id": "temporal_002",
                    "title": "Part 2: Deep Dive",
                    "channel_name": "TestChannel",
                    "published_at": "2025-05-05T10:00:00Z",
                    "content": "Continuing from part 1"
                },
                "expect_temporal": True,
                "days_apart": 4
            },
            {
                "name": "over_week",
                "transcript1": {
                    "video_id": "temporal_003",
                    "title": "Old Video",
                    "channel_name": "TestChannel",
                    "published_at": "2025-04-01T10:00:00Z",
                    "content": "Content from last month"
                },
                "transcript2": {
                    "video_id": "temporal_004",
                    "title": "New Video",
                    "channel_name": "TestChannel",
                    "published_at": "2025-05-01T10:00:00Z",
                    "content": "Content from this month"
                },
                "expect_temporal": False,
                "days_apart": 30
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            start_time = datetime.now()
            
            try:
                relationships = graph_memory.extract_relationships_between_transcripts(
                    test_case["transcript1"],
                    test_case["transcript2"]
                )
                
                # Check for temporal relationship
                temporal_rels = [r for r in relationships if r["type"] == "PUBLISHED_NEAR"]
                has_temporal = len(temporal_rels) > 0
                
                # Verify days apart if temporal relationship found
                correct_days = True
                if temporal_rels:
                    days_apart = temporal_rels[0].get("properties", {}).get("days_apart", -1)
                    correct_days = abs(days_apart - test_case["days_apart"]) <= 1  # Allow 1 day tolerance
                
                test_passed = has_temporal == test_case["expect_temporal"] and correct_days
                all_passed = all_passed and test_passed
                
                duration = (datetime.now() - start_time).total_seconds()
                
                self.results.append({
                    "test_name": f"Temporal Relationship - {test_case['name']}",
                    "status": "PASS" if test_passed else "FAIL",
                    "expected_temporal": test_case["expect_temporal"],
                    "found_temporal": has_temporal,
                    "expected_days": test_case["days_apart"],
                    "found_days": temporal_rels[0].get("properties", {}).get("days_apart") if temporal_rels else None,
                    "duration": f"{duration:.3f}s"
                })
                
            except Exception as e:
                all_passed = False
                self.results.append({
                    "test_name": f"Temporal Relationship - {test_case['name']}",
                    "status": "ERROR",
                    "error": str(e),
                    "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
                })
        
        assert all_passed, "Not all temporal relationship tests passed"
    
    def test_shared_entity_relationships(self):
        """Test shared entity relationship detection"""
        print("\n🔄 Testing Shared Entity Relationships...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Shared Entity Relationships",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        # Transcripts with known shared entities
        transcript1 = {
            "video_id": "entity_001",
            "title": "OpenAI's GPT-4 Architecture",
            "channel_name": "AINews",
            "published_at": "2025-05-01T10:00:00Z",
            "content": """
                OpenAI released GPT-4 with significant improvements. Microsoft partnered
                with OpenAI on this project. The transformer architecture shows major advances.
                Sam Altman discussed the implications for AI safety.
            """
        }
        
        transcript2 = {
            "video_id": "entity_002",
            "title": "Microsoft and OpenAI Partnership",
            "channel_name": "TechUpdates",
            "published_at": "2025-05-02T10:00:00Z",
            "content": """
                Microsoft's collaboration with OpenAI continues to deepen. GPT-4 integration
                into Microsoft products is underway. The transformer models are being optimized
                for Azure deployment. Sam Altman and Satya Nadella announced new initiatives.
            """
        }
        
        start_time = datetime.now()
        
        try:
            relationships = graph_memory.extract_relationships_between_transcripts(
                transcript1, transcript2
            )
            
            # Find shared entity relationships
            shared_entity_rels = [r for r in relationships if r["type"] == "SHARES_ENTITY"]
            
            # Extract shared entities
            shared_entities = set()
            for rel in shared_entity_rels:
                entity_name = rel.get("properties", {}).get("entity_name", "")
                if entity_name:
                    shared_entities.add(entity_name.lower())
            
            # Check for expected shared entities
            expected_shared = {"openai", "microsoft", "gpt-4", "sam altman"}
            found_shared = shared_entities & expected_shared
            
            # Test passes if we find at least 2 expected shared entities
            test_passed = len(found_shared) >= 2
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.results.append({
                "test_name": "Shared Entity Relationships",
                "status": "PASS" if test_passed else "FAIL",
                "total_shared_entities": len(shared_entities),
                "expected_shared": list(expected_shared),
                "found_shared": list(found_shared),
                "all_shared_entities": list(shared_entities),
                "match_rate": f"{len(found_shared)/len(expected_shared)*100:.0f}%",
                "duration": f"{duration:.3f}s"
            })
            
            assert test_passed, f"Shared entity test failed: found_shared={len(found_shared)}, expected_shared={len(expected_shared)}"
            
        except Exception as e:
            self.results.append({
                "test_name": "Shared Entity Relationships",
                "status": "ERROR",
                "error": str(e),
                "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
            })
            raise
    
    @staticmethod
    def generate_report(cls):
        """Generate test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path("docs/reports") / f"relationship_extraction_test_report_{timestamp}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate statistics
        total_tests = len(cls.results)
        passed = sum(1 for r in cls.results if r.get("status") == "PASS")
        failed = sum(1 for r in cls.results if r.get("status") == "FAIL")
        errors = sum(1 for r in cls.results if r.get("status") == "ERROR")
        skipped = sum(1 for r in cls.results if r.get("status") == "SKIPPED")
        
        report = f"""# Relationship Extraction Test Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Module**: GraphMemoryIntegration.extract_relationships_between_transcripts()

## Summary

- **Total Tests**: {total_tests}
- **Passed**: {passed} ✅
- **Failed**: {failed} ❌
- **Errors**: {errors} 🚫
- **Skipped**: {skipped} ⏭️
- **Success Rate**: {(passed/total_tests*100) if total_tests > 0 else 0:.1f}%

## Test Results

| Test Name | Status | Key Metrics | Duration |
|-----------|--------|-------------|----------|
"""
        
        for result in cls.results:
            status_emoji = {
                "PASS": "✅",
                "FAIL": "❌",
                "ERROR": "🚫",
                "SKIPPED": "⏭️"
            }.get(result.get("status", ""), "❓")
            
            # Extract key metrics
            metrics = ""
            if "f1_score" in result:
                metrics = f"F1: {result['f1_score']}, Found: {result['total_relationships']} relationships"
            elif "match_rate" in result:
                metrics = f"Match: {result['match_rate']}, Shared: {result['total_shared_entities']} entities"
            elif "found_temporal" in result:
                metrics = f"Temporal: {result['found_temporal']}, Days: {result.get('found_days', 'N/A')}"
            elif "reason" in result:
                metrics = result["reason"]
            elif "error" in result:
                metrics = f"Error: {result['error'][:50]}..."
            
            report += f"| {result.get('test_name', 'Unknown')} | {status_emoji} {result.get('status', 'Unknown')} | {metrics} | {result.get('duration', 'N/A')} |\n"
        
        # Add detailed results
        report += "\n## Detailed Results\n"
        
        for result in cls.results:
            if any(key in result for key in ["relationship_details", "found_shared", "expected_types"]):
                report += f"\n### {result.get('test_name', 'Unknown')}\n"
                
                # Select relevant details to show
                details = {}
                if "relationship_details" in result:
                    details["relationships"] = result["relationship_details"]
                if "found_types" in result:
                    details["types"] = {
                        "found": result["found_types"],
                        "expected": result["expected_types"],
                        "matched": result.get("matched_types", [])
                    }
                if "found_shared" in result:
                    details["shared_entities"] = {
                        "found": result["found_shared"],
                        "all": result.get("all_shared_entities", [])
                    }
                
                report += "```json\n"
                report += json.dumps(details, indent=2)
                report += "\n```\n"
        
        # Write report
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"\n📊 Test report saved to: {report_file}")
        return report_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])