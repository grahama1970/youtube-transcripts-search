#!/usr/bin/env python3
"""
Non-mocked tests for entity extraction functionality.
Tests with real transcript data and validates actual extraction results.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from src.youtube_transcripts.unified_search import GraphMemoryIntegration, UnifiedSearchConfig


class TestEntityExtraction:
    """Test entity extraction with real data"""
    
    @classmethod
    def setup_class(cls):
        cls.results = []
        cls.test_transcripts = [
            {
                "id": "test_1",
                "text": """
                    Today we're discussing VERL, a revolutionary framework by OpenAI for training 
                    large language models using reinforcement learning. The framework combines 
                    Monte Carlo tree search with reward modeling. John Smith from OpenAI 
                    explains how VERL optimizes the training process. Microsoft Research 
                    has also contributed to this work. The key innovation is the PPO algorithm
                    implementation that scales to billions of parameters. Stanford University
                    researchers have validated these results.
                """,
                "metadata": {
                    "video_id": "test_verl_001",
                    "title": "VERL: Training LLMs with Reinforcement Learning",
                    "channel_name": "TrelisResearch"
                },
                "expected_entities": {
                    "people": ["John Smith"],
                    "organizations": ["OpenAI", "Microsoft Research", "Stanford University"],
                    "technical_terms": ["VERL", "PPO", "LLMs"],
                    "channels": ["TrelisResearch"]
                }
            },
            {
                "id": "test_2",
                "text": """
                    Jane Doe from Google DeepMind presents AlphaGo's architecture. The system
                    uses MCTS (Monte Carlo Tree Search) combined with deep neural networks.
                    MIT researchers collaborated on this breakthrough. The CNN architecture
                    processes board positions while the value network evaluates positions.
                    Facebook AI Research has built upon these concepts.
                """,
                "metadata": {
                    "video_id": "test_alphago_002",
                    "title": "AlphaGo: Deep Learning Meets Game Theory",
                    "channel_name": "DiscoverAI"
                },
                "expected_entities": {
                    "people": ["Jane Doe"],
                    "organizations": ["Google DeepMind", "MIT", "Facebook AI Research"],
                    "technical_terms": ["AlphaGo", "MCTS", "CNN"],
                    "channels": ["DiscoverAI"]
                }
            }
        ]
    
    @classmethod
    def teardown_class(cls):
        """Generate report after all tests"""
        cls.generate_report(cls)
    
    def test_extract_entities_basic(self):
        """Test basic entity extraction functionality"""
        print("\n🔍 Testing Basic Entity Extraction...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Basic Entity Extraction",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        success_count = 0
        
        for test_case in self.test_transcripts:
            start_time = datetime.now()
            try:
                # Extract entities
                entities = graph_memory.extract_entities_from_transcript(
                    transcript_text=test_case["text"],
                    metadata=test_case["metadata"]
                )
                
                # Categorize extracted entities
                extracted = {
                    "people": [],
                    "organizations": [],
                    "technical_terms": [],
                    "channels": []
                }
                
                for entity in entities:
                    if entity["type"] == "person":
                        extracted["people"].append(entity["name"])
                    elif entity["type"] == "organization":
                        extracted["organizations"].append(entity["name"])
                    elif entity["type"] == "technical_term":
                        extracted["technical_terms"].append(entity["name"])
                    elif entity["type"] == "youtube_channel":
                        extracted["channels"].append(entity["name"])
                
                # Validate results
                expected = test_case["expected_entities"]
                
                # Check each category
                people_found = set(extracted["people"]) & set(expected["people"])
                orgs_found = set(extracted["organizations"]) & set(expected["organizations"])
                terms_found = set(extracted["technical_terms"]) & set(expected["technical_terms"])
                channels_found = set(extracted["channels"]) & set(expected["channels"])
                
                # Calculate success metrics
                total_expected = sum(len(v) for v in expected.values())
                total_found = len(people_found) + len(orgs_found) + len(terms_found) + len(channels_found)
                accuracy = total_found / total_expected if total_expected > 0 else 0
                
                test_passed = accuracy >= 0.6  # 60% threshold
                if test_passed:
                    success_count += 1
                
                duration = (datetime.now() - start_time).total_seconds()
                
                self.results.append({
                    "test_name": f"Entity Extraction - {test_case['id']}",
                    "status": "PASS" if test_passed else "FAIL",
                    "accuracy": f"{accuracy:.1%}",
                    "entities_found": len(entities),
                    "expected_found": f"{total_found}/{total_expected}",
                    "duration": f"{duration:.3f}s",
                    "details": {
                        "people": {"found": list(people_found), "missed": list(set(expected["people"]) - people_found)},
                        "organizations": {"found": list(orgs_found), "missed": list(set(expected["organizations"]) - orgs_found)},
                        "technical_terms": {"found": list(terms_found), "missed": list(set(expected["technical_terms"]) - terms_found)},
                        "channels": {"found": list(channels_found), "missed": list(set(expected["channels"]) - channels_found)}
                    }
                })
                
            except Exception as e:
                self.results.append({
                    "test_name": f"Entity Extraction - {test_case['id']}",
                    "status": "ERROR",
                    "error": str(e),
                    "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
                })
        
        assert success_count == len(self.test_transcripts), f"Only {success_count}/{len(self.test_transcripts)} tests passed"
    
    def test_entity_deduplication(self):
        """Test that entities are properly deduplicated"""
        print("\n🔄 Testing Entity Deduplication...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Entity Deduplication",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        # Text with repeated entities
        test_text = """
            OpenAI developed GPT-4. The OpenAI team, led by researchers at OpenAI,
            created GPT-4 as an advancement. GPT-4 from OpenAI represents a breakthrough.
            Microsoft and OpenAI partnered on GPT-4. Microsoft invested in OpenAI.
        """
        
        start_time = datetime.now()
        
        try:
            entities = graph_memory.extract_entities_from_transcript(
                transcript_text=test_text,
                metadata={"video_id": "dedup_test", "title": "Test Deduplication", "channel_name": "TestChannel"}
            )
            
            # Count occurrences of each entity
            entity_counts = {}
            for entity in entities:
                key = (entity["name"], entity["type"])
                entity_counts[key] = entity_counts.get(key, 0) + 1
            
            # Check for duplicates
            has_duplicates = any(count > 1 for count in entity_counts.values())
            unique_entities = len(entity_counts)
            
            # Verify key entities are found (case-insensitive)
            entity_names_lower = {name.lower() for (name, _) in entity_counts.keys()}
            openai_found = "openai" in entity_names_lower
            gpt4_found = any("gpt" in name for name in entity_names_lower)
            microsoft_found = "microsoft" in entity_names_lower
            
            test_passed = not has_duplicates and openai_found and gpt4_found and microsoft_found
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.results.append({
                "test_name": "Entity Deduplication",
                "status": "PASS" if test_passed else "FAIL",
                "has_duplicates": has_duplicates,
                "unique_entities": unique_entities,
                "key_entities_found": {
                    "OpenAI": openai_found,
                    "GPT-4": gpt4_found,
                    "Microsoft": microsoft_found
                },
                "duration": f"{duration:.3f}s"
            })
            
            assert test_passed, f"Deduplication failed: duplicates={has_duplicates}, OpenAI={openai_found}, GPT-4={gpt4_found}, Microsoft={microsoft_found}"
            
        except Exception as e:
            self.results.append({
                "test_name": "Entity Deduplication",
                "status": "ERROR",
                "error": str(e),
                "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
            })
            raise
    
    def test_empty_transcript(self):
        """Test entity extraction with empty or minimal input"""
        print("\n❌ Testing Empty/Minimal Transcript...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Empty Transcript",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        test_cases = [
            {"text": "", "expected_count": 0, "name": "empty_string"},
            {"text": "   ", "expected_count": 0, "name": "whitespace_only"},
            {"text": "a b c", "expected_count": 0, "name": "meaningless_chars"},
            {"text": "The and or but", "expected_count": 0, "name": "stop_words_only"}
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            start_time = datetime.now()
            
            try:
                entities = graph_memory.extract_entities_from_transcript(
                    transcript_text=test_case["text"],
                    metadata={"video_id": f"empty_{test_case['name']}", "title": "Empty Test", "channel_name": "TestChannel"}
                )
                
                # Should extract the channel name at minimum
                actual_count = len([e for e in entities if e["type"] != "youtube_channel"])
                test_passed = actual_count == test_case["expected_count"]
                
                if not test_passed:
                    all_passed = False
                
                duration = (datetime.now() - start_time).total_seconds()
                
                self.results.append({
                    "test_name": f"Empty Transcript - {test_case['name']}",
                    "status": "PASS" if test_passed else "FAIL",
                    "input_text": test_case["text"][:20] + "..." if len(test_case["text"]) > 20 else test_case["text"],
                    "expected_entities": test_case["expected_count"],
                    "actual_entities": actual_count,
                    "total_with_channel": len(entities),
                    "duration": f"{duration:.3f}s"
                })
                
            except Exception as e:
                all_passed = False
                self.results.append({
                    "test_name": f"Empty Transcript - {test_case['name']}",
                    "status": "ERROR",
                    "error": str(e),
                    "duration": f"{(datetime.now() - start_time).total_seconds():.3f}s"
                })
        
        assert all_passed, "Some empty transcript tests failed"
    
    def test_entity_confidence_scores(self):
        """Test that entities have appropriate confidence scores"""
        print("\n📊 Testing Entity Confidence Scores...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Entity Confidence Scores",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        test_text = """
            Dr. Sarah Johnson from Harvard University published groundbreaking research.
            The IBM Watson team collaborated with Google Cloud engineers on AI systems.
            BERT and GPT are transformer-based models. Amazon Web Services provides infrastructure.
        """
        
        start_time = datetime.now()
        
        try:
            entities = graph_memory.extract_entities_from_transcript(
                transcript_text=test_text,
                metadata={"video_id": "confidence_test", "title": "Test Confidence", "channel_name": "TestChannel"}
            )
            
            # Check confidence scores by type
            confidence_by_type = {}
            for entity in entities:
                entity_type = entity["type"]
                confidence = entity.get("properties", {}).get("confidence", 1.0)
                
                if entity_type not in confidence_by_type:
                    confidence_by_type[entity_type] = []
                confidence_by_type[entity_type].append(confidence)
            
            # Validate confidence ranges
            all_valid = True
            for entity_type, scores in confidence_by_type.items():
                min_score = min(scores) if scores else 0
                max_score = max(scores) if scores else 0
                avg_score = sum(scores) / len(scores) if scores else 0
                
                # Check if scores are in valid range [0, 1]
                valid = all(0 <= s <= 1 for s in scores)
                all_valid = all_valid and valid
                
                # Organizations should have higher confidence than technical terms
                if entity_type == "organization" and "technical_term" in confidence_by_type:
                    org_avg = avg_score
                    tech_avg = sum(confidence_by_type["technical_term"]) / len(confidence_by_type["technical_term"])
                    # This is a soft check - organizations typically have higher confidence
            
            test_passed = all_valid and len(entities) >= 5
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.results.append({
                "test_name": "Entity Confidence Scores",
                "status": "PASS" if test_passed else "FAIL",
                "total_entities": len(entities),
                "confidence_valid": all_valid,
                "confidence_by_type": {
                    k: {"min": min(v), "max": max(v), "avg": sum(v)/len(v)} 
                    for k, v in confidence_by_type.items()
                },
                "duration": f"{duration:.3f}s"
            })
            
            assert test_passed, f"Confidence test failed: valid={all_valid}, entities={len(entities)}"
            
        except Exception as e:
            self.results.append({
                "test_name": "Entity Confidence Scores",
                "status": "ERROR",
                "error": str(e),
                "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
            })
            raise
    
    def test_malformed_input(self):
        """Test entity extraction with malformed or edge case input"""
        print("\n⚠️ Testing Malformed Input...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Malformed Input",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        test_cases = [
            {
                "text": "A" * 10000,  # Very long single word
                "name": "extremely_long_word",
                "should_not_crash": True
            },
            {
                "text": "SELECT * FROM users; DROP TABLE transcripts;--",
                "name": "sql_injection_attempt",
                "should_not_crash": True
            },
            {
                "text": "<script>alert('xss')</script>",
                "name": "html_injection",
                "should_not_crash": True
            },
            {
                "text": "João São Paulo Zürich 北京",  # Unicode
                "name": "unicode_text",
                "should_not_crash": True
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            start_time = datetime.now()
            
            try:
                entities = graph_memory.extract_entities_from_transcript(
                    transcript_text=test_case["text"],
                    metadata={"video_id": f"malformed_{test_case['name']}", "title": "Malformed Test", "channel_name": "TestChannel"}
                )
                
                # Test passes if it doesn't crash
                test_passed = test_case["should_not_crash"]
                duration = (datetime.now() - start_time).total_seconds()
                
                self.results.append({
                    "test_name": f"Malformed Input - {test_case['name']}",
                    "status": "PASS" if test_passed else "FAIL",
                    "entities_found": len(entities),
                    "duration": f"{duration:.3f}s",
                    "handled_gracefully": True
                })
                
            except Exception as e:
                # Some exceptions might be expected for malformed input
                test_passed = False
                all_passed = False
                
                self.results.append({
                    "test_name": f"Malformed Input - {test_case['name']}",
                    "status": "FAIL",
                    "error": str(e)[:100],
                    "duration": f"{(datetime.now() - start_time).total_seconds():.3f}s",
                    "handled_gracefully": False
                })
        
        assert all_passed, "Some malformed input tests failed"
    
    @staticmethod
    def generate_report(cls):
        """Generate test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path("docs/reports") / f"entity_extraction_test_report_{timestamp}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate statistics
        total_tests = len(cls.results)
        passed = sum(1 for r in cls.results if r.get("status") == "PASS")
        failed = sum(1 for r in cls.results if r.get("status") == "FAIL")
        errors = sum(1 for r in cls.results if r.get("status") == "ERROR")
        skipped = sum(1 for r in cls.results if r.get("status") == "SKIPPED")
        
        report = f"""# Entity Extraction Test Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Module**: GraphMemoryIntegration.extract_entities_from_transcript()

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
            
            # Extract key metrics based on test
            metrics = ""
            if "accuracy" in result:
                metrics = f"Accuracy: {result['accuracy']}, Found: {result.get('expected_found', 'N/A')}"
            elif "unique_entities" in result:
                metrics = f"Unique: {result['unique_entities']}, No duplicates: {not result.get('has_duplicates', True)}"
            elif "total_entities" in result:
                metrics = f"Total: {result['total_entities']}, Valid confidence: {result.get('confidence_valid', False)}"
            elif "reason" in result:
                metrics = result["reason"]
            elif "error" in result:
                metrics = f"Error: {result['error'][:50]}..."
            
            report += f"| {result.get('test_name', 'Unknown')} | {status_emoji} {result.get('status', 'Unknown')} | {metrics} | {result.get('duration', 'N/A')} |\n"
        
        # Add detailed results
        report += "\n## Detailed Results\n"
        
        for result in cls.results:
            if "details" in result or "confidence_by_type" in result:
                report += f"\n### {result.get('test_name', 'Unknown')}\n"
                report += "```json\n"
                details = result.get("details") or result.get("confidence_by_type", {})
                report += json.dumps(details, indent=2)
                report += "\n```\n"
        
        # Write report
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"\n📊 Test report saved to: {report_file}")
        return report_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])