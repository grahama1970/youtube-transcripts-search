"""
Advanced citation detector using SpaCy patterns and Ollama for context.

This module provides robust citation detection beyond simple regex, using
SpaCy's pattern matching and Ollama for understanding citation context.

External Documentation:
- SpaCy Matcher: https://spacy.io/usage/rule-based-matching
- Ollama: https://ollama.ai/

Sample Input:
    "Our work builds on BERT (Devlin et al., 2019) and the recent paper
    'Attention is All You Need' by Vaswani et al. (2017). See also
    arXiv:2301.00234 and doi:10.1038/nature12373."

Expected Output:
    [
        {'type': 'author_year', 'text': 'Devlin et al., 2019', 
         'context': 'Our work builds on BERT'},
        {'type': 'paper_title', 'text': 'Attention is All You Need',
         'authors': 'Vaswani et al. (2017)'},
        {'type': 'arxiv', 'id': '2301.00234'},
        {'type': 'doi', 'id': '10.1038/nature12373'}
    ]
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span

# Import Ollama if available
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False
    ollama = None

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Represents a detected citation."""
    type: str  # 'arxiv', 'doi', 'author_year', 'paper_title'
    text: str  # Full citation text
    id: Optional[str] = None  # Extracted ID (for arxiv, doi)
    authors: Optional[str] = None  # Author names
    year: Optional[str] = None  # Publication year
    title: Optional[str] = None  # Paper title
    context: Optional[str] = None  # Surrounding context
    confidence: float = 1.0  # Confidence score
    position: Optional[Tuple[int, int]] = None  # Start, end positions


class CitationDetector:
    """Advanced citation detection using NLP techniques."""
    
    def __init__(self, spacy_model: str = "en_core_web_sm", 
                 use_ollama: bool = True,
                 ollama_model: str = "qwen2.5:3b"):
        """Initialize the citation detector.
        
        Args:
            spacy_model: SpaCy model to use
            use_ollama: Whether to use Ollama for context understanding
            ollama_model: Ollama model for citation extraction
        """
        # Load SpaCy
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", spacy_model], check=True)
            self.nlp = spacy.load(spacy_model)
        
        # Initialize matcher for citation patterns
        self.matcher = Matcher(self.nlp.vocab)
        self._add_citation_patterns()
        
        # Ollama settings
        self.use_ollama = use_ollama and HAS_OLLAMA
        self.ollama_model = ollama_model
        
        if self.use_ollama and not HAS_OLLAMA:
            logger.warning("Ollama requested but not available. Install with: pip install ollama")
    
    def _add_citation_patterns(self):
        """Add SpaCy patterns for citation detection."""
        
        # Pattern: (Author et al., YEAR)
        et_al_pattern = [
            {"TEXT": "("},
            {"POS": "PROPN"},  # Author name
            {"TEXT": "et", "OP": "?"},
            {"TEXT": "al", "OP": "?"},
            {"TEXT": {"IN": [".", ","]}},
            {"SHAPE": "dddd"},  # Year
            {"TEXT": ")"}
        ]
        self.matcher.add("ET_AL_CITATION", [et_al_pattern])
        
        # Pattern: Author and Author (YEAR)
        multi_author_pattern = [
            {"TEXT": "("},
            {"POS": "PROPN"},
            {"TEXT": {"IN": ["and", "&"]}},
            {"POS": "PROPN"},
            {"TEXT": "("},
            {"SHAPE": "dddd"},
            {"TEXT": ")"}
        ]
        self.matcher.add("MULTI_AUTHOR_CITATION", [multi_author_pattern])
        
        # Pattern: "Paper Title" by Author
        title_pattern = [
            {"TEXT": '"'},
            {"OP": "+"},  # One or more tokens for title
            {"TEXT": '"'},
            {"TEXT": "by", "OP": "?"},
            {"POS": "PROPN", "OP": "+"}  # Author names
        ]
        self.matcher.add("PAPER_TITLE", [title_pattern])
    
    def detect_citations(self, text: str) -> List[Citation]:
        """Detect all citations in the text.
        
        Args:
            text: Input text
            
        Returns:
            List of detected citations
        """
        citations = []
        
        # Detect structured citations (arXiv, DOI)
        citations.extend(self._detect_structured_citations(text))
        
        # Process with SpaCy for author-year citations
        doc = self.nlp(text)
        citations.extend(self._detect_author_citations(doc))
        
        # Use Ollama for advanced detection if available
        if self.use_ollama:
            ollama_citations = self._detect_with_ollama(text)
            citations.extend(ollama_citations)
        
        # Deduplicate and sort by position
        citations = self._deduplicate_citations(citations)
        citations.sort(key=lambda c: c.position[0] if c.position else 0)
        
        return citations
    
    def _detect_structured_citations(self, text: str) -> List[Citation]:
        """Detect arXiv IDs, DOIs, and other structured citations."""
        citations = []
        
        # arXiv pattern with optional version
        arxiv_pattern = re.compile(r'\b(?:arXiv:?\s*)?(\d{4}\.\d{4,5}(?:v\d+)?)\b', re.IGNORECASE)
        for match in arxiv_pattern.finditer(text):
            citations.append(Citation(
                type='arxiv',
                text=match.group(0),
                id=match.group(1),
                position=(match.start(), match.end()),
                context=self._extract_context(text, match.start(), match.end())
            ))
        
        # DOI pattern
        doi_pattern = re.compile(r'\b(?:doi:?\s*|https?://doi\.org/)?'
                                r'(10\.\d{4,}/[-._;()/:\w]+)\b', re.IGNORECASE)
        for match in doi_pattern.finditer(text):
            citations.append(Citation(
                type='doi',
                text=match.group(0),
                id=match.group(1),
                position=(match.start(), match.end()),
                context=self._extract_context(text, match.start(), match.end())
            ))
        
        # ISBN pattern
        isbn_pattern = re.compile(r'\b(?:ISBN[-\s]?)?'
                                 r'(97[89][-\s]?\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,6}[-\s]?\d)\b',
                                 re.IGNORECASE)
        for match in isbn_pattern.finditer(text):
            citations.append(Citation(
                type='isbn',
                text=match.group(0),
                id=match.group(1).replace('-', '').replace(' ', ''),
                position=(match.start(), match.end())
            ))
        
        return citations
    
    def _detect_author_citations(self, doc: Doc) -> List[Citation]:
        """Detect author-year style citations using SpaCy."""
        citations = []
        
        # Use matcher for patterns
        matches = self.matcher(doc)
        
        for match_id, start, end in matches:
            span = doc[start:end]
            match_label = self.nlp.vocab.strings[match_id]
            
            if match_label in ["ET_AL_CITATION", "MULTI_AUTHOR_CITATION"]:
                # Extract author and year
                text = span.text
                year_match = re.search(r'\d{4}', text)
                if year_match:
                    citations.append(Citation(
                        type='author_year',
                        text=text,
                        year=year_match.group(),
                        position=(span.start_char, span.end_char),
                        context=self._extract_context(doc.text, span.start_char, span.end_char)
                    ))
        
        # Also look for simpler patterns
        simple_pattern = re.compile(r'([A-Z][a-z]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][a-z]+)*)'
                                   r'(?:\s*\(\s*(\d{4})\s*\)|\s*,?\s*(\d{4}))')
        
        for match in simple_pattern.finditer(doc.text):
            authors = match.group(1)
            year = match.group(2) or match.group(3)
            
            citations.append(Citation(
                type='author_year',
                text=match.group(0),
                authors=authors,
                year=year,
                position=(match.start(), match.end()),
                context=self._extract_context(doc.text, match.start(), match.end())
            ))
        
        return citations
    
    def _detect_with_ollama(self, text: str) -> List[Citation]:
        """Use Ollama for advanced citation detection."""
        if not self.use_ollama:
            return []
        
        try:
            # Chunk text if too long
            max_chunk_size = 2000
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size-200)]
            
            all_citations = []
            
            for chunk in chunks:
                prompt = f"""Extract all academic citations from the following text. 
                Include paper titles, author names with years, arXiv IDs, and DOIs.
                Format each citation as JSON with fields: type, text, authors, year, title.
                
                Text: {chunk}
                
                Return only the JSON array of citations, nothing else."""
                
                response = ollama.generate(
                    model=self.ollama_model,
                    prompt=prompt
                )
                
                try:
                    # Parse Ollama response
                    citations_json = response['response']
                    # Extract JSON from response
                    json_match = re.search(r'\[.*\]', citations_json, re.DOTALL)
                    if json_match:
                        citations_data = json.loads(json_match.group())
                        
                        for cite_data in citations_data:
                            citation = Citation(
                                type=cite_data.get('type', 'unknown'),
                                text=cite_data.get('text', ''),
                                authors=cite_data.get('authors'),
                                year=cite_data.get('year'),
                                title=cite_data.get('title'),
                                confidence=0.8  # Lower confidence for Ollama results
                            )
                            all_citations.append(citation)
                
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to parse Ollama response: {e}")
            
            return all_citations
            
        except Exception as e:
            logger.error(f"Ollama citation detection failed: {e}")
            return []
    
    def _extract_context(self, text: str, start: int, end: int, 
                        context_window: int = 50) -> str:
        """Extract surrounding context for a citation."""
        context_start = max(0, start - context_window)
        context_end = min(len(text), end + context_window)
        
        context = text[context_start:context_end]
        
        # Mark the citation in context
        citation_start = start - context_start
        citation_end = end - context_start
        
        return context
    
    def _deduplicate_citations(self, citations: List[Citation]) -> List[Citation]:
        """Remove duplicate citations, keeping the most detailed version."""
        seen = {}
        
        for citation in citations:
            # Create a key for deduplication
            key = f"{citation.type}:{citation.id or citation.text}"
            
            if key not in seen:
                seen[key] = citation
            else:
                # Keep the one with more information
                existing = seen[key]
                if (len(citation.text) > len(existing.text) or
                    citation.confidence > existing.confidence):
                    seen[key] = citation
        
        return list(seen.values())
    
    def format_for_export(self, citations: List[Citation], 
                         format: str = 'bibtex') -> str:
        """Format citations for export.
        
        Args:
            citations: List of citations to format
            format: Export format ('bibtex', 'json', 'markdown')
            
        Returns:
            Formatted string
        """
        if format == 'bibtex':
            return self._format_bibtex(citations)
        elif format == 'json':
            return self._format_json(citations)
        elif format == 'markdown':
            return self._format_markdown(citations)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _format_bibtex(self, citations: List[Citation]) -> str:
        """Format citations as BibTeX entries."""
        entries = []
        
        for i, cite in enumerate(citations):
            if cite.type == 'arxiv':
                entry = f"""@article{{arxiv{i},
  title = {{{cite.title or 'arXiv:' + cite.id}}},
  author = {{{cite.authors or 'Unknown'}}},
  year = {{{cite.year or '2024'}}},
  eprint = {{{cite.id}}},
  archivePrefix = {{arXiv}}
}}"""
            elif cite.type == 'doi':
                entry = f"""@article{{doi{i},
  title = {{{cite.title or 'Article'}}},
  author = {{{cite.authors or 'Unknown'}}},
  year = {{{cite.year or '2024'}}},
  doi = {{{cite.id}}}
}}"""
            else:
                entry = f"""@misc{{cite{i},
  title = {{{cite.title or cite.text}}},
  author = {{{cite.authors or 'Unknown'}}},
  year = {{{cite.year or '2024'}}}
}}"""
            
            entries.append(entry)
        
        return '\n\n'.join(entries)
    
    def _format_json(self, citations: List[Citation]) -> str:
        """Format citations as JSON."""
        data = []
        for cite in citations:
            data.append({
                'type': cite.type,
                'text': cite.text,
                'id': cite.id,
                'authors': cite.authors,
                'year': cite.year,
                'title': cite.title,
                'context': cite.context,
                'confidence': cite.confidence
            })
        return json.dumps(data, indent=2)
    
    def _format_markdown(self, citations: List[Citation]) -> str:
        """Format citations as Markdown list."""
        lines = ["# Citations\n"]
        
        for cite in citations:
            if cite.type == 'arxiv':
                line = f"- [{cite.id}](https://arxiv.org/abs/{cite.id})"
            elif cite.type == 'doi':
                line = f"- [{cite.id}](https://doi.org/{cite.id})"
            else:
                line = f"- {cite.text}"
            
            if cite.title:
                line += f" - *{cite.title}*"
            if cite.authors and cite.year:
                line += f" ({cite.authors}, {cite.year})"
            
            lines.append(line)
        
        return '\n'.join(lines)


if __name__ == "__main__":
    # Test the citation detector
    detector = CitationDetector(use_ollama=False)  # Disable Ollama for testing
    
    test_texts = [
        """Recent advances in language models have been remarkable. The seminal 
        work "Attention is All You Need" by Vaswani et al. (2017) introduced 
        the transformer architecture. This was followed by BERT (Devlin et al., 2019)
        and GPT-3 (Brown et al., 2020).
        
        For more details, see arXiv:1706.03762 and the paper at 
        doi:10.1162/neco.2020.32.8.1466. The book by Goodfellow et al. 2016
        provides excellent background.""",
        
        """In Smith and Johnson (2023), the authors propose a new framework.
        This builds on earlier work (Liu et al., 2022; Wang & Chen, 2021).
        See also the preprint at arXiv:2301.00234v2."""
    ]
    
    print("=== Citation Detection Test ===\n")
    
    for i, text in enumerate(test_texts, 1):
        print(f"Test {i}:")
        print(f"Text: {text[:100]}...\n")
        
        citations = detector.detect_citations(text)
        
        print(f"Found {len(citations)} citations:")
        for cite in citations:
            print(f"  - Type: {cite.type}")
            print(f"    Text: {cite.text}")
            if cite.id:
                print(f"    ID: {cite.id}")
            if cite.authors:
                print(f"    Authors: {cite.authors}")
            if cite.year:
                print(f"    Year: {cite.year}")
            print()
        
        # Test export formats
        if citations:
            print("BibTeX format:")
            print(detector.format_for_export(citations[:2], 'bibtex'))
            print("\n" + "="*50 + "\n")
    
    print("✓ Citation detection test complete!")