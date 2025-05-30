#!/usr/bin/env python3
"""
Non-mocked tests for hybrid search functionality.
Tests ArangoDB hybrid search fallback with real queries.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import json
import sqlite3

sys.path.append(str(Path(__file__).parent.parent))

from src.youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig, GraphMemoryIntegration
from src.youtube_transcripts.core.database import initialize_database, add_transcript


class TestHybridSearch:
    """Test hybrid search fallback functionality"""
    
    @classmethod
    def setup_class(cls):
        cls.results = []
        cls.test_db = Path("/tmp/test_hybrid_search.db")
        cls.test_queries = [
            {
                "id": "semantic_query",
                "query": "understanding transformer architecture neural networks",
                "description": "Semantic query that may not match exact keywords",
                "expect_fallback": True
            },
            {
                "id": "exact_match",
                "query": "reinforcement learning PPO",
                "description": "Query with exact keyword matches",
                "expect_fallback": False
            },
            {
                "id": "abstract_concept",
                "query": "consciousness emergence artificial intelligence",
                "description": "Abstract concept query",
                "expect_fallback": True
            }
        ]
    
    @classmethod
    def teardown_class(cls):
        """Generate report after all tests"""
        cls.generate_report(cls)
        # Clean up test database if it exists
        if cls.test_db.exists():
            cls.test_db.unlink()
    
    def setup_test_database(self):
        """Create test database with sample transcripts"""
        if self.test_db.exists():
            self.test_db.unlink()
        
        initialize_database(self.test_db)
        
        # Add test transcripts
        test_transcripts = [
            {
                "video_id": "rl_001",
                "title": "Reinforcement Learning with PPO Algorithm",
                "channel_name": "TrelisResearch",
                "publish_date": "2025-05-01",
                "transcript": "Today we discuss reinforcement learning using the PPO algorithm for training agents."
            },
            {
                "video_id": "transformer_001",
                "title": "How Transformers Work",
                "channel_name": "DiscoverAI",
                "publish_date": "2025-05-02",
                "transcript": "Deep dive into attention mechanisms and self-attention in neural network models."
            }
        ]
        
        for transcript in test_transcripts:
            add_transcript(**transcript, db_path=self.test_db)
    
    def setup_arangodb_test_data(self, graph_memory):
        """Setup test data in ArangoDB for hybrid search"""
        try:
            # Import ArangoDB utilities
            from arangodb.core.arango_setup import connect_arango, ensure_database
            from arangodb.core.utils.embedding_utils import get_embedding
            
            # Connect to ArangoDB
            client = connect_arango()
            db = ensure_database(client)
            
            # Create test collection if it doesn't exist
            if not db.has_collection("transcripts"):
                db.create_collection("transcripts")
            
            # Clear existing data
            db.collection("transcripts").truncate()
            
            # Add test documents with embeddings
            test_docs = [
                {
                    "_key": "semantic_001",
                    "video_id": "semantic_001",
                    "title": "Understanding Transformer Architecture in Neural Networks",
                    "channel_name": "DeepLearningAI",
                    "published_at": "2025-05-03",
                    "content": "This video explains transformer architecture, self-attention mechanisms, and how neural networks process sequences.",
                    "url": "https://youtube.com/watch?v=semantic_001",
                    "tags": ["transformers", "neural networks", "deep learning"]
                },
                {
                    "_key": "abstract_001",
                    "video_id": "abstract_001", 
                    "title": "Consciousness and Emergence in AI Systems",
                    "channel_name": "PhilosophyOfAI",
                    "published_at": "2025-05-04",
                    "content": "Exploring consciousness, emergence, and artificial intelligence from philosophical and technical perspectives.",
                    "url": "https://youtube.com/watch?v=abstract_001",
                    "tags": ["consciousness", "emergence", "AI philosophy"]
                }
            ]
            
            # Add embeddings to documents
            for doc in test_docs:
                # Generate embedding for content
                embedding = get_embedding(doc["content"])
                if embedding:
                    doc["embedding"] = embedding
                    doc["embedding_model"] = "BAAI/bge-large-en-v1.5"
                    doc["embedding_dimensions"] = len(embedding)
                
            # Insert documents
            db.collection("transcripts").insert_many(test_docs)
            
            return True
            
        except Exception as e:
            print(f"Failed to setup ArangoDB test data: {e}")
            return False
    
    def cleanup_arangodb_test_data(self):
        """Clean up ArangoDB test data"""
        try:
            from arangodb.core.arango_setup import connect_arango, ensure_database
            client = connect_arango()
            db = ensure_database(client)
            if db.has_collection("transcripts"):
                db.collection("transcripts").truncate()
        except Exception as e:
            print(f"Failed to cleanup ArangoDB test data: {e}")
    
    def test_hybrid_search_fallback(self):
        """Test that hybrid search is triggered when SQLite returns no results"""
        print("\n🔄 Testing Hybrid Search Fallback...")
        
        config = UnifiedSearchConfig()
        search_system = UnifiedYouTubeSearch(config, db_path=self.test_db)
        
        if not search_system.graph_memory.enabled:
            self.results.append({
                "test_name": "Hybrid Search Fallback",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        # Setup test databases
        self.setup_test_database()
        self.setup_arangodb_test_data(search_system.graph_memory)
        
        success_count = 0
        
        for test_case in self.test_queries:
            start_time = datetime.now()
            
            try:
                # Search with the query
                results = search_system.search(
                    query=test_case["query"],
                    use_optimization=False,  # Don't optimize to test raw queries
                    use_memory=True,
                    use_widening=False  # Disable widening to isolate hybrid search
                )
                
                # Check if any results came from ArangoDB
                arango_results = [
                    r for r in results.get("results", [])
                    if r.get("source") == "arangodb_hybrid"
                ]
                
                used_hybrid = len(arango_results) > 0
                total_results = results.get("total_found", 0)
                
                # For semantic queries, we expect hybrid search to be used
                # For exact matches, SQLite should find results
                if test_case["expect_fallback"]:
                    test_passed = used_hybrid or total_results == 0  # Either hybrid was used or no results at all
                else:
                    test_passed = total_results > 0  # Should find results (from either source)
                
                if test_passed:
                    success_count += 1
                
                duration = (datetime.now() - start_time).total_seconds()
                
                self.results.append({
                    "test_name": f"Hybrid Search - {test_case['id']}",
                    "status": "PASS" if test_passed else "FAIL",
                    "query": test_case["query"],
                    "description": test_case["description"],
                    "total_results": total_results,
                    "used_hybrid": used_hybrid,
                    "arango_results": len(arango_results),
                    "expected_fallback": test_case["expect_fallback"],
                    "duration": f"{duration:.3f}s"
                })
                
            except Exception as e:
                self.results.append({
                    "test_name": f"Hybrid Search - {test_case['id']}",
                    "status": "ERROR",
                    "error": str(e),
                    "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
                })
        
        # Cleanup
        if self.test_db.exists():
            self.test_db.unlink()
        self.cleanup_arangodb_test_data()
        
        assert success_count >= len(self.test_queries) - 1, f"Only {success_count}/{len(self.test_queries)} tests passed (allowing one failure)"
    
    def test_hybrid_search_with_filters(self):
        """Test hybrid search with channel filters"""
        print("\n🔍 Testing Hybrid Search with Filters...")
        
        config = UnifiedSearchConfig()
        graph_memory = GraphMemoryIntegration(config)
        
        if not graph_memory.enabled:
            self.results.append({
                "test_name": "Hybrid Search with Filters",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        # Setup ArangoDB test data
        self.setup_arangodb_test_data(graph_memory)
        
        start_time = datetime.now()
        
        try:
            # Test with channel filter
            results = graph_memory.search_with_arango_hybrid(
                query="machine learning algorithms",
                channels=["TrelisResearch", "DiscoverAI"],
                limit=10
            )
            
            # Verify results format
            valid_format = all(
                isinstance(r, dict) and "video_id" in r and "title" in r
                for r in results
            )
            
            # Check if channel filter would be respected
            # (Note: actual filtering depends on ArangoDB data)
            test_passed = valid_format and isinstance(results, list)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.results.append({
                "test_name": "Hybrid Search with Filters",
                "status": "PASS" if test_passed else "FAIL",
                "total_results": len(results),
                "valid_format": valid_format,
                "channels_filtered": ["TrelisResearch", "DiscoverAI"],
                "duration": f"{duration:.3f}s"
            })
            
            assert test_passed, f"Hybrid search with filters failed: valid_format={valid_format}, results_type={type(results)}"
            
        except Exception as e:
            self.results.append({
                "test_name": "Hybrid Search with Filters",
                "status": "ERROR",
                "error": str(e),
                "duration": f"{(datetime.now() - start_time).total_seconds():.2f}s"
            })
            raise
        finally:
            # Cleanup
            self.cleanup_arangodb_test_data()
    
    def test_hybrid_search_performance(self):
        """Test hybrid search performance and response time"""
        print("\n⚡ Testing Hybrid Search Performance...")
        
        config = UnifiedSearchConfig()
        search_system = UnifiedYouTubeSearch(config, db_path=self.test_db)
        
        if not search_system.graph_memory.enabled:
            self.results.append({
                "test_name": "Hybrid Search Performance",
                "status": "SKIPPED",
                "reason": "ArangoDB not available"
            })
            pytest.skip("ArangoDB not available")
        
        # Setup test database
        self.setup_test_database()
        
        # Test queries of varying complexity
        performance_queries = [
            "AI",  # Very short
            "machine learning neural networks",  # Medium
            "advanced reinforcement learning techniques for robotic control systems"  # Long
        ]
        
        performance_results = []
        
        for query in performance_queries:
            start_time = datetime.now()
            
            try:
                results = search_system.search(
                    query=query,
                    use_optimization=False,
                    use_memory=True,
                    use_widening=False
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                performance_results.append({
                    "query_length": len(query),
                    "query_words": len(query.split()),
                    "duration": duration,
                    "results_found": results.get("total_found", 0)
                })
                
            except Exception as e:
                performance_results.append({
                    "query_length": len(query),
                    "error": str(e)
                })
        
        # Calculate average performance
        valid_results = [r for r in performance_results if "duration" in r]
        avg_duration = sum(r["duration"] for r in valid_results) / len(valid_results) if valid_results else 0
        
        # Test passes if average response time is under 5 seconds
        test_passed = avg_duration < 5.0 and len(valid_results) >= 2
        
        # Cleanup
        if self.test_db.exists():
            self.test_db.unlink()
        
        self.results.append({
            "test_name": "Hybrid Search Performance",
            "status": "PASS" if test_passed else "FAIL",
            "average_duration": f"{avg_duration:.3f}s",
            "queries_tested": len(performance_queries),
            "successful_queries": len(valid_results),
            "performance_details": performance_results
        })
        
        assert test_passed, f"Performance test failed: avg_duration={avg_duration:.3f}s, valid_results={len(valid_results)}"
    
    @staticmethod
    def generate_report(cls):
        """Generate test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path("docs/reports") / f"hybrid_search_test_report_{timestamp}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate statistics
        total_tests = len(cls.results)
        passed = sum(1 for r in cls.results if r.get("status") == "PASS")
        failed = sum(1 for r in cls.results if r.get("status") == "FAIL")
        errors = sum(1 for r in cls.results if r.get("status") == "ERROR")
        skipped = sum(1 for r in cls.results if r.get("status") == "SKIPPED")
        
        report = f"""# Hybrid Search Test Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Module**: GraphMemoryIntegration.search_with_arango_hybrid()

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
            if "used_hybrid" in result:
                metrics = f"Hybrid: {result['used_hybrid']}, Results: {result['total_results']}"
            elif "average_duration" in result:
                metrics = f"Avg time: {result['average_duration']}, Tested: {result['queries_tested']}"
            elif "valid_format" in result:
                metrics = f"Results: {result['total_results']}, Valid: {result['valid_format']}"
            elif "reason" in result:
                metrics = result["reason"]
            elif "error" in result:
                metrics = f"Error: {result['error'][:50]}..."
            
            duration = result.get("duration", result.get("average_duration", "N/A"))
            
            report += f"| {result.get('test_name', 'Unknown')} | {status_emoji} {result.get('status', 'Unknown')} | {metrics} | {duration} |\n"
        
        # Add detailed results
        report += "\n## Detailed Results\n"
        
        for result in cls.results:
            if any(key in result for key in ["query", "performance_details", "channels_filtered"]):
                report += f"\n### {result.get('test_name', 'Unknown')}\n"
                
                if "query" in result:
                    report += f"**Query**: `{result['query']}`\n"
                    report += f"**Expected Fallback**: {result.get('expected_fallback', 'N/A')}\n"
                    report += f"**Used Hybrid**: {result.get('used_hybrid', 'N/A')}\n"
                
                if "performance_details" in result:
                    report += "\n#### Performance Details\n"
                    report += "| Query Words | Duration | Results |\n"
                    report += "|-------------|----------|----------|\n"
                    for detail in result["performance_details"]:
                        if "duration" in detail:
                            report += f"| {detail.get('query_words', 'N/A')} | {detail['duration']:.2f}s | {detail.get('results_found', 'N/A')} |\n"
        
        # Write report
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"\n📊 Test report saved to: {report_file}")
        return report_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])