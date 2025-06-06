"""
Scientific metadata extractor for YouTube transcripts.
Module: metadata_extractor.py
Description: Implementation of metadata extractor functionality

Coordinates extraction of academic metadata using SpaCy, Transformers, and
existing NLP infrastructure. Integrates with claude-module-communicator for
progress tracking.

External Documentation:
- SpaCy: https://spacy.io/
- Transformers: https://huggingface.co/docs/transformers/
- Claude Module Communicator: https://github.com/grahama1970/claude-module-communicator

Sample Input:
    Transcript object with text containing academic content

Expected Output:
    {
        'urls': ['https://arxiv.org/abs/2301.00001'],
        'institutions': ['MIT', 'Stanford'],
        'keywords': ['machine learning', 'neural networks'],
        'technical_terms': ['BERT', 'GPT-4', 'transformer'],
        'citations': [{'type': 'arxiv', 'id': '2301.00001'}, ...],
        'speakers': [{'name': 'Dr. Smith', 'affiliation': 'MIT'}]
    }
"""

import logging
import re
from typing import Any

from youtube_transcripts.core.models import Transcript
from youtube_transcripts.core.utils.embedding_wrapper import EmbeddingUtils
from youtube_transcripts.core.utils.spacy_scientific import ScientificPipeline

# Try to import claude-module-communicator for progress tracking
try:
    from claude_module_communicator import ModuleCommunicator, ProgressTracker
    HAS_CMC = True
except ImportError:
    HAS_CMC = False
    ModuleCommunicator = None
    ProgressTracker = None

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts scientific metadata from YouTube transcripts."""

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        """Initialize the metadata extractor.
        
        Args:
            spacy_model: SpaCy model to use
        """
        self.pipeline = ScientificPipeline(spacy_model)
        self.embedding_utils = EmbeddingUtils()

        # Initialize progress tracking if available
        self.progress_tracker = None
        if HAS_CMC:
            try:
                self.progress_tracker = ProgressTracker("metadata_extraction")
            except Exception as e:
                logger.warning(f"Could not initialize progress tracker: {e}")

    def extract_urls(self, text: str) -> list[str]:
        """Extract URLs from text.
        
        Args:
            text: Input text
            
        Returns:
            List of unique URLs found
        """
        # Comprehensive URL pattern
        url_pattern = re.compile(
            r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}'
            r'(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        )

        urls = list(set(url_pattern.findall(text)))

        # Filter out common false positives
        filtered_urls = []
        for url in urls:
            # Skip if it ends with punctuation (likely part of sentence)
            if url[-1] in '.,:;!?)':
                url = url[:-1]
            filtered_urls.append(url)

        return filtered_urls

    def extract_keywords(self, text: str, top_k: int = 20) -> list[str]:
        """Extract important keywords using embeddings and frequency.
        
        Args:
            text: Input text
            top_k: Number of keywords to extract
            
        Returns:
            List of important keywords
        """
        # Process with SpaCy
        doc = self.pipeline.nlp(text)

        # Get noun phrases and technical terms
        candidates = set()

        # Add noun phrases
        for chunk in doc.noun_chunks:
            if 2 <= len(chunk.text.split()) <= 4:
                candidates.add(chunk.text.lower())

        # Add technical terms from pipeline
        candidates.update(doc._.technical_terms)

        # Filter candidates
        keywords = []
        for candidate in candidates:
            # Skip very short or very common terms
            if len(candidate) < 3:
                continue

            # Check if it appears multiple times (importance indicator)
            count = text.lower().count(candidate.lower())
            if count >= 2 or any(char.isupper() for char in candidate):
                keywords.append((candidate, count))

        # Sort by frequency and return top k
        keywords.sort(key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in keywords[:top_k]]

    def format_citations(self, citations: list[tuple]) -> list[dict[str, str]]:
        """Format raw citations into structured format.
        
        Args:
            citations: List of (type, text, start, end) tuples
            
        Returns:
            List of formatted citation dictionaries
        """
        formatted = []
        seen = set()

        for cite_type, text, start, end in citations:
            # Avoid duplicates
            key = f"{cite_type}:{text}"
            if key in seen:
                continue
            seen.add(key)

            citation = {
                'type': cite_type,
                'text': text,
                'position': {'start': start, 'end': end}
            }

            # Add specific fields based on type
            if cite_type == 'arxiv':
                citation['id'] = text
                citation['url'] = f"https://arxiv.org/abs/{text}"
            elif cite_type == 'doi':
                citation['id'] = text
                citation['url'] = f"https://doi.org/{text}"

            formatted.append(citation)

        return formatted

    def extract_metadata(self, transcript: Transcript) -> dict[str, Any]:
        """Extract all scientific metadata from a transcript.
        
        Args:
            transcript: Transcript object to process
            
        Returns:
            Dictionary containing all extracted metadata
        """
        if self.progress_tracker:
            self.progress_tracker.start_operation(
                f"Extracting metadata for transcript {transcript.video_id}"
            )

        try:
            # Process with SpaCy pipeline
            results = self.pipeline.process_transcript(transcript.text)

            # Extract additional metadata
            urls = self.extract_urls(transcript.text)
            keywords = self.extract_keywords(transcript.text)

            # Format citations
            formatted_citations = self.format_citations(results.get('citations', []))

            # Combine all metadata
            metadata = {
                'urls': urls,
                'institutions': results.get('institutions', []),
                'keywords': keywords,
                'technical_terms': results.get('technical_terms', []),
                'citations': formatted_citations,
                'speakers': results.get('speakers', []),
                'conferences': results.get('conferences', []),
                'people': results.get('people', [])
            }

            # Add extraction timestamp
            from datetime import datetime
            metadata['extracted_at'] = datetime.utcnow().isoformat()

            if self.progress_tracker:
                self.progress_tracker.complete_operation(
                    f"Extracted {len(formatted_citations)} citations, "
                    f"{len(metadata['institutions'])} institutions"
                )

            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            if self.progress_tracker:
                self.progress_tracker.fail_operation(str(e))
            raise

    def extract_batch(self, transcripts: list[Transcript]) -> dict[str, dict[str, Any]]:
        """Extract metadata from multiple transcripts.
        
        Args:
            transcripts: List of transcript objects
            
        Returns:
            Dictionary mapping video_id to metadata
        """
        results = {}

        for transcript in transcripts:
            try:
                metadata = self.extract_metadata(transcript)
                results[transcript.video_id] = metadata
            except Exception as e:
                logger.error(f"Failed to extract metadata for {transcript.video_id}: {e}")
                results[transcript.video_id] = {'error': str(e)}

        return results


if __name__ == "__main__":
    # Test with sample transcript
    from src.youtube_transcripts.core.models import Transcript

    # Create test transcript
    test_transcript = Transcript(
        video_id="test_001",
        title="Deep Learning Lecture at MIT",
        channel_name="MIT OpenCourseWare",
        text="""Welcome to MIT. I'm Professor Sarah Johnson from the Computer Science 
        department. Today we'll discuss our recent paper on transformer architectures 
        published in NeurIPS 2023. The work, available at arXiv:2301.00234, builds 
        on BERT (Devlin et al., 2019) and GPT-3.
        
        Our collaboration with Stanford University and DeepMind resulted in VERL,
        a new framework for video understanding. You can find more details at
        https://github.com/mit-ai/verl and https://verl.ai/papers/main.pdf.
        
        The key contributions include multi-modal fusion, temporal reasoning, and
        efficient attention mechanisms. We achieved state-of-the-art results on
        ActivityNet and Kinetics-400 benchmarks.""",
        publish_date="2024-01-15",
        duration=3600
    )

    # Test extraction
    extractor = MetadataExtractor()

    print("=== Metadata Extraction Test ===\n")
    print(f"Video: {test_transcript.title}")
    print(f"Channel: {test_transcript.channel_name}\n")

    metadata = extractor.extract_metadata(test_transcript)

    print("Extracted Metadata:")
    for key, value in metadata.items():
        if value and key != 'extracted_at':
            print(f"\n{key}:")
            if isinstance(value, list):
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"  {value}")

    print("\n✓ Metadata extraction test complete!")
