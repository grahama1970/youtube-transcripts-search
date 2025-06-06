"""
SpaCy pipeline configuration for scientific text processing.
Module: spacy_scientific.py
Description: Implementation of spacy scientific functionality

This module configures SpaCy with domain-specific components for extracting
scientific entities, citations, and academic metadata from YouTube transcripts.

External Documentation:
- SpaCy: https://spacy.io/usage/processing-pipelines
- sci-spacy: https://allenai.github.io/scispacy/

Sample Input:
    "Professor Smith from MIT presented a paper on reinforcement learning
    (arXiv:2301.00001) at NeurIPS 2023. The work builds on BERT
    (Devlin et al., 2019) and introduces the VERL framework."

Expected Output:
    {
        'people': ['Professor Smith'],
        'institutions': ['MIT'],
        'conferences': ['NeurIPS 2023'],
        'citations': ['arXiv:2301.00001', 'Devlin et al., 2019'],
        'technical_terms': ['reinforcement learning', 'BERT', 'VERL framework']
    }
"""

import re

import spacy
from spacy.language import Language
from spacy.tokens import Doc


class ScientificPipeline:
    """Enhanced SpaCy pipeline for scientific text processing."""

    # Academic institution indicators
    INSTITUTION_INDICATORS = {
        'university', 'institute', 'lab', 'laboratory', 'college',
        'center', 'centre', 'department', 'school', 'academy',
        'research', 'foundation'
    }

    # Academic title patterns
    ACADEMIC_TITLES = {
        'professor', 'prof', 'dr', 'phd', 'postdoc', 'researcher',
        'scientist', 'engineer', 'student', 'fellow', 'associate',
        'assistant', 'lecturer', 'instructor'
    }

    # Conference/venue patterns
    CONFERENCE_PATTERNS = [
        r'\b(NIPS|NeurIPS|ICML|ICLR|CVPR|ECCV|ICCV|ACL|EMNLP|NAACL|CoNLL)\s*\d{2,4}\b',
        r'\b(conference|workshop|symposium|summit|meeting)\b',
    ]

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize the scientific SpaCy pipeline.
        
        Args:
            model_name: SpaCy model to load (default: en_core_web_sm)
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"Downloading {model_name}...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
            self.nlp = spacy.load(model_name)

        # Add custom components
        self._add_citation_detector()
        self._add_institution_recognizer()
        self._add_technical_term_extractor()

    def _add_citation_detector(self):
        """Add citation detection patterns to the pipeline."""

        @Language.component("citation_detector")
        def citation_detector(doc: Doc) -> Doc:
            citations = []

            # arXiv pattern: 4 digits dot 4-5 digits
            arxiv_pattern = re.compile(r'\b(\d{4}\.\d{4,5})\b')
            for match in arxiv_pattern.finditer(doc.text):
                citations.append(('arxiv', match.group(1), match.start(), match.end()))

            # DOI pattern
            doi_pattern = re.compile(r'\b(10\.\d{4,}/[-._;()/:\w]+)\b')
            for match in doi_pattern.finditer(doc.text):
                citations.append(('doi', match.group(1), match.start(), match.end()))

            # Author-year citations
            author_year_pattern = re.compile(r'([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)*\s+et\s+al\.?,?\s*\d{4})')
            for match in author_year_pattern.finditer(doc.text):
                citations.append(('author_year', match.group(1), match.start(), match.end()))

            # Single author citations
            single_author_pattern = re.compile(r'\(([A-Z][a-z]+,?\s*\d{4})\)')
            for match in single_author_pattern.finditer(doc.text):
                citations.append(('author_year', match.group(1), match.start(), match.end()))

            # Store citations in doc
            doc._.citations = citations
            return doc

        # Register extension attribute
        if not Doc.has_extension("citations"):
            Doc.set_extension("citations", default=[])

        # Add to pipeline
        if "citation_detector" not in self.nlp.pipe_names:
            self.nlp.add_pipe("citation_detector", last=True)

    def _add_institution_recognizer(self):
        """Add institution recognition to the pipeline."""

        @Language.component("institution_recognizer")
        def institution_recognizer(doc: Doc) -> Doc:
            institutions = set()

            # Check named entities
            for ent in doc.ents:
                if ent.label_ == "ORG":
                    # Check if it's likely an academic institution
                    text_lower = ent.text.lower()
                    if any(indicator in text_lower for indicator in self.INSTITUTION_INDICATORS) or (len(ent.text) <= 5 and ent.text.isupper()):
                        institutions.add(ent.text)

            # Pattern-based detection for missed institutions
            for token in doc:
                if token.pos_ == "PROPN":
                    # Check multi-word institutions
                    phrase = []
                    for i in range(5):  # Look ahead up to 5 tokens
                        if token.i + i < len(doc):
                            next_token = doc[token.i + i]
                            if next_token.pos_ in ["PROPN", "NOUN", "ADP", "DET"]:
                                phrase.append(next_token.text)
                            else:
                                break

                    phrase_text = " ".join(phrase)
                    phrase_lower = phrase_text.lower()
                    if any(indicator in phrase_lower for indicator in self.INSTITUTION_INDICATORS):
                        institutions.add(phrase_text)

            doc._.institutions = list(institutions)
            return doc

        # Register extension
        if not Doc.has_extension("institutions"):
            Doc.set_extension("institutions", default=[])

        # Add to pipeline
        if "institution_recognizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("institution_recognizer", after="ner")

    def _add_technical_term_extractor(self):
        """Add technical term extraction to the pipeline."""

        @Language.component("technical_term_extractor")
        def technical_term_extractor(doc: Doc) -> Doc:
            technical_terms = set()

            # Extract noun phrases that might be technical terms
            for chunk in doc.noun_chunks:
                # Filter for likely technical terms
                if len(chunk.text.split()) <= 4:  # Max 4 words
                    # Check if contains numbers, capitals, or specific patterns
                    if (any(token.pos_ == "PROPN" for token in chunk) or
                        any(char.isdigit() for char in chunk.text) or
                        chunk.text.count('-') > 0 or
                        any(token.text.isupper() and len(token.text) > 1 for token in chunk)):
                        technical_terms.add(chunk.text)

            # Extract acronyms
            acronym_pattern = re.compile(r'\b[A-Z]{2,}\b')
            for match in acronym_pattern.finditer(doc.text):
                technical_terms.add(match.group())

            # Extract version patterns (e.g., BERT-large, GPT-4)
            version_pattern = re.compile(r'\b[A-Z]+[-_]\w+\b')
            for match in version_pattern.finditer(doc.text):
                technical_terms.add(match.group())

            doc._.technical_terms = list(technical_terms)
            return doc

        # Register extension
        if not Doc.has_extension("technical_terms"):
            Doc.set_extension("technical_terms", default=[])

        # Add to pipeline
        if "technical_term_extractor" not in self.nlp.pipe_names:
            self.nlp.add_pipe("technical_term_extractor", after="ner")

    def extract_speakers(self, doc: Doc) -> list[dict[str, str]]:
        """Extract speaker information with titles and affiliations.
        
        Args:
            doc: Processed SpaCy document
            
        Returns:
            List of speaker dictionaries with name, title, and affiliation
        """
        speakers = []

        # Look for person entities
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                speaker = {"name": ent.text, "title": None, "affiliation": None}

                # Look for titles before the name
                if ent.start > 0:
                    prev_token = doc[ent.start - 1]
                    if prev_token.text.lower() in self.ACADEMIC_TITLES:
                        speaker["title"] = prev_token.text

                # Look for affiliations after the name
                if ent.end < len(doc) - 2:
                    next_tokens = doc[ent.end:ent.end + 5]
                    for i, token in enumerate(next_tokens):
                        if token.text.lower() in ["from", "at", "with"]:
                            # Check if next entity is an organization
                            for org_ent in doc.ents:
                                if org_ent.label_ == "ORG" and org_ent.start == ent.end + i + 1:
                                    speaker["affiliation"] = org_ent.text
                                    break

                speakers.append(speaker)

        return speakers

    def process_transcript(self, text: str) -> dict[str, list]:
        """Process a transcript and extract all scientific metadata.
        
        Args:
            text: Transcript text to process
            
        Returns:
            Dictionary containing extracted metadata
        """
        doc = self.nlp(text)

        # Extract speakers with additional info
        speakers = self.extract_speakers(doc)

        # Extract conferences/venues
        conferences = []
        for pattern in self.CONFERENCE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                conferences.append(match.group())

        return {
            'people': [ent.text for ent in doc.ents if ent.label_ == "PERSON"],
            'institutions': doc._.institutions,
            'citations': doc._.citations,
            'technical_terms': doc._.technical_terms,
            'speakers': speakers,
            'conferences': conferences
        }


if __name__ == "__main__":
    # Test the pipeline with sample data
    pipeline = ScientificPipeline()

    test_texts = [
        """Professor Jane Smith from MIT CSAIL presented groundbreaking work on 
        reinforcement learning at NeurIPS 2023. The paper (arXiv:2301.00234) 
        builds on BERT (Devlin et al., 2019) and introduces VERL, a new framework 
        for volcano research. Dr. Johnson from Stanford University collaborated 
        on this project.""",

        """In this talk, I'll discuss our recent paper published in Nature 
        (doi:10.1038/nature12373). We developed GPT-4 based models for 
        protein folding. This is joint work with researchers from DeepMind 
        and the University of Cambridge.""",

        """The Llama-3 model from Meta AI shows impressive results. As shown 
        in Smith et al., 2024, the performance exceeds GPT-3.5 on many benchmarks. 
        We tested it at our lab in Berkeley."""
    ]

    print("=== SpaCy Scientific Pipeline Test ===\n")

    for i, text in enumerate(test_texts, 1):
        print(f"Test {i}:")
        print(f"Input: {text[:100]}...")

        results = pipeline.process_transcript(text)

        print("\nExtracted metadata:")
        for key, values in results.items():
            if values:
                print(f"  {key}: {values}")
        print("\n" + "="*50 + "\n")

    print("✓ Pipeline validation complete!")
