# youtube_transcripts/src/youtube_transcripts/search_widener.py
"""
Progressive search widening system for YouTube transcript search.
Implements incremental query expansion when no results are found.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import re
from youtube_transcripts.core.database import search_transcripts
from pathlib import Path

@dataclass
class SearchWidenerResult:
    """Result from search widening process"""
    original_query: str
    final_query: str
    widening_technique: str
    widening_level: int
    results: List[Dict[str, Any]]
    explanation: str


class SearchWidener:
    """
    Implements progressive search widening strategies
    to find results when initial queries return nothing.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        
    def search_with_widening(
        self, 
        query: str, 
        channel_names: Optional[List[str]] = None,
        max_widening_level: int = 4
    ) -> SearchWidenerResult:
        """
        Perform search with progressive widening if no results found.
        
        Args:
            query: Initial search query
            channel_names: Optional list of channels to filter
            max_widening_level: Maximum widening attempts
            
        Returns:
            SearchWidenerResult with results and explanation
        """
        original_query = query
        current_query = query
        widening_level = 0
        technique_used = "exact match"
        
        # Try original query first
        results = self._execute_search(current_query, channel_names)
        
        if results:
            return SearchWidenerResult(
                original_query=original_query,
                final_query=current_query,
                widening_technique=technique_used,
                widening_level=widening_level,
                results=results,
                explanation=f"Found {len(results)} results with exact query."
            )
        
        # Progressive widening strategies
        widening_strategies = [
            (self._add_synonyms, "synonym expansion"),
            (self._stem_words, "word stemming"),
            (self._fuzzy_matching, "fuzzy matching"),
            (self._semantic_expansion, "semantic expansion")
        ]
        
        for widener_func, technique_name in widening_strategies[:max_widening_level]:
            widening_level += 1
            current_query = widener_func(original_query)
            results = self._execute_search(current_query, channel_names)
            
            if results:
                explanation = self._generate_explanation(
                    original_query, current_query, technique_name, widening_level, len(results)
                )
                
                return SearchWidenerResult(
                    original_query=original_query,
                    final_query=current_query,
                    widening_technique=technique_name,
                    widening_level=widening_level,
                    results=results,
                    explanation=explanation
                )
        
        # No results found even after widening
        return SearchWidenerResult(
            original_query=original_query,
            final_query=current_query,
            widening_technique="all techniques exhausted",
            widening_level=widening_level,
            results=[],
            explanation=f"No results found for '{original_query}' even after trying {widening_level} widening techniques."
        )
    
    def _execute_search(self, query: str, channel_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Execute the actual search"""
        kwargs = {}
        if self.db_path:
            kwargs['db_path'] = self.db_path
        
        return search_transcripts(
            query=query,
            channel_names=channel_names,
            limit=20,
            **kwargs
        )
    
    def _add_synonyms(self, query: str) -> str:
        """Add common synonyms and related terms"""
        # Instead of using OR operators which cause FTS5 syntax errors,
        # we'll expand the query by adding synonym terms
        synonyms = {
            'VERL': ['VERL', 'Volcano', 'Engine', 'Reinforcement', 'Learning'],
            'RL': ['RL', 'Reinforcement', 'Learning', 'machine', 'learning'],
            'AI': ['AI', 'Artificial', 'Intelligence', 'machine', 'learning'],
            'LLM': ['LLM', 'Large', 'Language', 'Model'],
            'tutorial': ['tutorial', 'guide', 'howto', 'walkthrough'],
            'setup': ['setup', 'install', 'configuration', 'deployment'],
        }
        
        words = query.split()
        expanded_words = []
        
        for word in words:
            if word.upper() in synonyms:
                # Add all synonyms as separate words
                expanded_words.extend(synonyms[word.upper()])
            elif word.lower() in synonyms:
                expanded_words.extend(synonyms[word.lower()])
            else:
                expanded_words.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for word in expanded_words:
            if word.lower() not in seen:
                seen.add(word.lower())
                result.append(word)
        
        return ' '.join(result)
    
    def _stem_words(self, query: str) -> str:
        """Apply basic word stemming to broaden search"""
        # Simple stemming rules
        words = query.split()
        stemmed_words = []
        
        for word in words:
            # Remove common suffixes
            stem = word
            for suffix in ['ing', 'ed', 's', 'er', 'est', 'ly']:
                if word.endswith(suffix) and len(word) > len(suffix) + 2:
                    stem = word[:-len(suffix)]
                    break
            
            # Add both original and stem as separate words
            stemmed_words.append(word)
            if stem != word:
                stemmed_words.append(stem)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for word in stemmed_words:
            if word.lower() not in seen:
                seen.add(word.lower())
                result.append(word)
        
        return ' '.join(result)
    
    def _fuzzy_matching(self, query: str) -> str:
        """Add fuzzy matching patterns"""
        words = query.split()
        fuzzy_words = []
        
        for word in words:
            if len(word) > 3:
                # Add wildcard for potential variations
                fuzzy_words.append(f"{word}*")
            else:
                fuzzy_words.append(word)
        
        return ' OR '.join(fuzzy_words)
    
    def _semantic_expansion(self, query: str) -> str:
        """Expand query with semantically related terms"""
        # Map of terms to their semantic relatives
        semantic_map = {
            'VERL': ['volcano', 'engine', 'reinforcement', 'learning', 'RL', 'framework'],
            'tutorial': ['guide', 'lesson', 'course', 'walkthrough', 'demo'],
            'setup': ['install', 'configure', 'deploy', 'initialization'],
            'optimization': ['optimize', 'improve', 'enhance', 'tune', 'performance'],
        }
        
        words = query.split()
        all_terms = set(words)
        
        for word in words:
            if word in semantic_map:
                all_terms.update(semantic_map[word])
        
        return ' OR '.join(all_terms)
    
    def _generate_explanation(
        self, 
        original: str, 
        widened: str, 
        technique: str, 
        level: int,
        result_count: int
    ) -> str:
        """Generate user-friendly explanation of widening"""
        explanations = {
            "synonym expansion": f"Expanded '{original}' with synonyms and related terms to find {result_count} results.",
            "word stemming": f"Applied word stemming to '{original}' (removing suffixes like -ing, -ed) to find {result_count} results.",
            "fuzzy matching": f"Used fuzzy matching with wildcards on '{original}' to find {result_count} similar results.",
            "semantic expansion": f"Expanded '{original}' with semantically related concepts to find {result_count} results."
        }
        
        base_explanation = explanations.get(technique, f"Applied {technique} to find results.")
        
        return f"No exact matches found for '{original}'. {base_explanation} (Widening level: {level})"


# Example usage
def demo_search_widening():
    """Demonstrate search widening functionality"""
    widener = SearchWidener()
    
    # Test queries that might need widening
    test_queries = [
        "VERL volcano engine",
        "reinforcment lerning",  # Typo
        "LLM fine tuning",
        "something that doesn't exist"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        result = widener.search_with_widening(query)
        
        print(f"Widening technique: {result.widening_technique}")
        print(f"Final query: {result.final_query}")
        print(f"Results found: {len(result.results)}")
        print(f"Explanation: {result.explanation}")
        
        if result.results:
            print("Top results:")
            for i, r in enumerate(result.results[:3]):
                print(f"  {i+1}. {r['title']} - {r['channel_name']}")


if __name__ == "__main__":
    demo_search_widening()