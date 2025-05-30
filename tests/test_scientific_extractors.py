"""
Comprehensive tests for scientific metadata extractors.

Tests all NLP-based extractors including SpaCy pipeline, citation detection,
speaker extraction, and content classification.
"""

import pytest
from pathlib import Path
import json
from typing import List, Dict, Any

from src.youtube_transcripts.core.models import Transcript
from src.youtube_transcripts.core.utils.spacy_scientific import ScientificPipeline
from src.youtube_transcripts.metadata_extractor import MetadataExtractor
from src.youtube_transcripts.citation_detector import CitationDetector, Citation
from src.youtube_transcripts.speaker_extractor import SpeakerExtractor, Speaker
from src.youtube_transcripts.content_classifier import ContentClassifier, ContentClassification


class TestScientificPipeline:
    """Test the SpaCy scientific pipeline."""
    
    def test_pipeline_initialization(self):
        """Test pipeline can be initialized."""
        pipeline = ScientificPipeline()
        assert pipeline.nlp is not None
        assert "citation_detector" in pipeline.nlp.pipe_names
        assert "institution_recognizer" in pipeline.nlp.pipe_names
        assert "technical_term_extractor" in pipeline.nlp.pipe_names
    
    def test_citation_detection(self):
        """Test citation detection in pipeline."""
        pipeline = ScientificPipeline()
        
        text = """Our work builds on BERT (Devlin et al., 2019) and recent 
        advances in transformers. See arXiv:2301.00234 for details. The DOI 
        is 10.1038/nature12373."""
        
        doc = pipeline.nlp(text)
        citations = doc._.citations
        
        assert len(citations) >= 3
        citation_types = [c[0] for c in citations]
        assert 'arxiv' in citation_types
        assert 'doi' in citation_types
        assert 'author_year' in citation_types
    
    def test_institution_recognition(self):
        """Test institution recognition."""
        pipeline = ScientificPipeline()
        
        text = """I'm from MIT's Computer Science department. We collaborated 
        with Stanford University and researchers at UC Berkeley."""
        
        doc = pipeline.nlp(text)
        institutions = doc._.institutions
        
        assert len(institutions) >= 2
        assert any('MIT' in inst for inst in institutions)
        assert any('Stanford' in inst for inst in institutions)
    
    def test_technical_term_extraction(self):
        """Test technical term extraction."""
        pipeline = ScientificPipeline()
        
        text = """We use BERT-large and GPT-4 models. The CNN architecture 
        includes batch normalization and dropout layers. Our RL agent uses 
        Q-learning."""
        
        doc = pipeline.nlp(text)
        terms = doc._.technical_terms
        
        assert len(terms) >= 4
        # Check for specific technical terms
        terms_lower = [t.lower() for t in terms]
        assert any('bert' in t for t in terms_lower)
        assert any('gpt' in t for t in terms_lower)
    
    def test_speaker_extraction_in_pipeline(self):
        """Test speaker extraction functionality."""
        pipeline = ScientificPipeline()
        
        text = """Hello, I'm Professor Jane Smith from Harvard Medical School. 
        Today we have Dr. Robert Chen from Johns Hopkins joining us."""
        
        speakers = pipeline.extract_speakers(pipeline.nlp(text))
        
        assert len(speakers) >= 2
        names = [s['name'] for s in speakers]
        assert any('Jane Smith' in name for name in names)
        assert any('Robert Chen' in name for name in names)


class TestCitationDetector:
    """Test the citation detector module."""
    
    def test_arxiv_detection(self):
        """Test arXiv ID detection."""
        detector = CitationDetector(use_ollama=False)
        
        text = """See our paper at arXiv:2301.00234 and the follow-up work 
        in 2302.00456. Also check arxiv:2303.12345v2 for the updated version."""
        
        citations = detector.detect_citations(text)
        arxiv_citations = [c for c in citations if c.type == 'arxiv']
        
        assert len(arxiv_citations) >= 3
        ids = [c.id for c in arxiv_citations]
        assert '2301.00234' in ids
        assert '2302.00456' in ids
        assert '2303.12345v2' in ids
    
    def test_doi_detection(self):
        """Test DOI detection."""
        detector = CitationDetector(use_ollama=False)
        
        text = """Published in Nature (doi:10.1038/nature12373) and Science 
        (DOI: 10.1126/science.1234567). See https://doi.org/10.1145/1234567.890123"""
        
        citations = detector.detect_citations(text)
        doi_citations = [c for c in citations if c.type == 'doi']
        
        assert len(doi_citations) >= 3
        ids = [c.id for c in doi_citations]
        assert '10.1038/nature12373' in ids
        assert '10.1126/science.1234567' in ids
    
    def test_author_year_detection(self):
        """Test author-year citation detection."""
        detector = CitationDetector(use_ollama=False)
        
        text = """Building on Vaswani et al. (2017) and Devlin et al., 2019. 
        See also Smith and Jones (2022) and the work by Liu et al. 2023."""
        
        citations = detector.detect_citations(text)
        author_citations = [c for c in citations if c.type == 'author_year']
        
        assert len(author_citations) >= 4
        years = [c.year for c in author_citations if c.year]
        assert '2017' in years
        assert '2019' in years
        assert '2022' in years
    
    def test_citation_formatting(self):
        """Test citation export formatting."""
        detector = CitationDetector(use_ollama=False)
        
        citations = [
            Citation(type='arxiv', text='arXiv:2301.00234', id='2301.00234'),
            Citation(type='doi', text='doi:10.1038/nature12373', id='10.1038/nature12373'),
            Citation(type='author_year', text='Smith et al., 2023', 
                    authors='Smith et al.', year='2023')
        ]
        
        # Test BibTeX format
        bibtex = detector._format_bibtex(citations)
        assert '@article{' in bibtex
        assert 'eprint = {2301.00234}' in bibtex
        assert 'doi = {10.1038/nature12373}' in bibtex
        
        # Test JSON format
        json_str = detector._format_json(citations)
        data = json.loads(json_str)
        assert len(data) == 3
        assert data[0]['type'] == 'arxiv'
        
        # Test Markdown format
        markdown = detector._format_markdown(citations)
        assert '[2301.00234](https://arxiv.org/abs/2301.00234)' in markdown
        assert '[10.1038/nature12373](https://doi.org/10.1038/nature12373)' in markdown


class TestSpeakerExtractor:
    """Test the speaker extractor module."""
    
    def test_introduction_extraction(self):
        """Test speaker extraction from introductions."""
        extractor = SpeakerExtractor()
        
        text = """Good morning. I'm Dr. Sarah Johnson from MIT's AI Lab. 
        Let me introduce Professor Wei Chen from Stanford University and 
        Dr. Patel from Microsoft Research."""
        
        speakers = extractor.extract_speakers(text)
        
        assert len(speakers) >= 3
        names = [s.name for s in speakers]
        assert any('Sarah Johnson' in n for n in names)
        assert any('Wei Chen' in n for n in names)
        
        # Check affiliations
        mit_speaker = next((s for s in speakers if 'MIT' in str(s.affiliation)), None)
        assert mit_speaker is not None
    
    def test_labeled_speaker_extraction(self):
        """Test extraction from labeled speakers."""
        extractor = SpeakerExtractor()
        
        text = """
        Speaker 1: Dr. Alice Cooper (University of Chicago)
        Speaker 2: Bob Wilson, CEO of TechCorp
        Moderator: Jane Smith from CNN
        """
        
        speakers = extractor.extract_speakers(text)
        
        assert len(speakers) >= 3
        
        # Check roles
        roles = [s.role for s in speakers if s.role]
        assert 'moderator' in roles
        
        # Check titles
        titles = [s.title for s in speakers if s.title]
        assert any('Dr.' in t for t in titles)
    
    def test_speaker_deduplication(self):
        """Test that duplicate speakers are merged."""
        extractor = SpeakerExtractor()
        
        text = """Professor Smith from MIT presented first. Later, 
        Prof. Smith showed more results. Dr. Smith from MIT concluded."""
        
        speakers = extractor.extract_speakers(text)
        
        # Should merge all Smith mentions
        smith_speakers = [s for s in speakers if 'Smith' in s.name]
        assert len(smith_speakers) == 1
        assert smith_speakers[0].affiliation == 'MIT'
    
    def test_speaker_formatting(self):
        """Test speaker output formatting."""
        extractor = SpeakerExtractor()
        
        speakers = [
            Speaker(name="Dr. Jane Smith", title="Dr.", 
                   affiliation="MIT", role="speaker"),
            Speaker(name="John Doe", affiliation="Stanford", 
                   role="moderator")
        ]
        
        # Test JSON format
        json_str = extractor.format_speakers(speakers, 'json')
        data = json.loads(json_str)
        assert len(data) == 2
        assert data[0]['name'] == "Dr. Jane Smith"
        
        # Test Markdown format
        markdown = extractor.format_speakers(speakers, 'markdown')
        assert '**Dr. Dr. Jane Smith**' in markdown
        assert '(MIT)' in markdown
        assert '*moderator*' in markdown


class TestContentClassifier:
    """Test the content classifier module."""
    
    def test_content_type_classification(self):
        """Test classification of content types."""
        classifier = ContentClassifier(use_ollama=False)
        
        # Test lecture detection
        lecture_transcript = Transcript(
            video_id="test_lecture",
            title="CS101 Lecture",
            channel_name="University",
            text="""Welcome to class. Today we will learn about algorithms. 
            Remember your homework is due next week. Office hours are at 3pm.""",
            publish_date="2024-01-01",
            duration=3600
        )
        
        result = classifier.classify_content(lecture_transcript)
        assert result.content_type == 'lecture'
        
        # Test tutorial detection
        tutorial_transcript = Transcript(
            video_id="test_tutorial",
            title="Python Tutorial",
            channel_name="CodeChannel",
            text="""In this tutorial, I'll show you how to build a web app 
            step by step. Let's start with the installation. First, install 
            Flask. Here's the example code.""",
            publish_date="2024-01-01",
            duration=1800
        )
        
        result = classifier.classify_content(tutorial_transcript)
        assert result.content_type == 'tutorial'
    
    def test_academic_level_classification(self):
        """Test classification of academic levels."""
        classifier = ContentClassifier(use_ollama=False)
        
        # Test undergraduate level
        undergrad = Transcript(
            video_id="test_undergrad",
            title="Intro to CS",
            channel_name="University",
            text="""This is CS 101, introduction to computer science. No prior 
            knowledge required. We'll start with the basics of programming.""",
            publish_date="2024-01-01",
            duration=3600
        )
        
        result = classifier.classify_content(undergrad)
        assert result.academic_level == 'undergraduate'
        
        # Test research level
        research = Transcript(
            video_id="test_research",
            title="Novel Approach to RL",
            channel_name="Conference",
            text="""We propose a novel approach to reinforcement learning. Our 
            contribution is threefold. Experiments show state-of-the-art results. 
            Future work includes scaling to larger datasets.""",
            publish_date="2024-01-01",
            duration=1800
        )
        
        result = classifier.classify_content(research)
        assert result.academic_level == 'research'
    
    def test_topic_extraction(self):
        """Test topic extraction using embeddings."""
        classifier = ContentClassifier(use_ollama=False)
        
        ml_transcript = Transcript(
            video_id="test_ml",
            title="Deep Learning",
            channel_name="AI Channel",
            text="""Today we'll discuss neural networks, backpropagation, and 
            gradient descent. We'll train a model on the MNIST dataset and 
            evaluate accuracy and loss. This builds on machine learning basics.""",
            publish_date="2024-01-01",
            duration=3600
        )
        
        result = classifier.classify_content(ml_transcript)
        assert 'machine_learning' in result.topics
        assert result.primary_topic in ['machine_learning', 'deep_learning']
    
    def test_quality_indicators(self):
        """Test calculation of quality indicators."""
        classifier = ContentClassifier(use_ollama=False)
        
        high_quality = Transcript(
            video_id="test_quality",
            title="Academic Lecture",
            channel_name="University",
            text="""In this lecture, we examine recent research by Smith et al. 
            (2023) on transformer architectures. First, we review the theoretical 
            foundations. Second, we analyze the methodology. Our hypothesis is 
            that attention mechanisms improve performance. Results show significant 
            improvements. See arXiv:2301.00234 for details. In conclusion, this 
            research provides empirical evidence for our theoretical model.""",
            publish_date="2024-01-01",
            duration=3600
        )
        
        result = classifier.classify_content(high_quality)
        indicators = result.quality_indicators
        
        assert indicators['citation_frequency'] > 0
        assert indicators['academic_language'] > 0.5
        assert indicators['structure_score'] > 0
        assert indicators['technical_density'] > 0


class TestMetadataExtractor:
    """Test the main metadata extractor."""
    
    def test_full_extraction(self):
        """Test complete metadata extraction."""
        extractor = MetadataExtractor()
        
        transcript = Transcript(
            video_id="test_full",
            title="ML Research Talk at MIT",
            channel_name="MIT",
            text="""Hello, I'm Professor Jane Smith from MIT CSAIL. Today I'll 
            present our paper "Transformers for Video Understanding" published 
            at NeurIPS 2023 (arXiv:2301.00234). This builds on BERT (Devlin 
            et al., 2019). Joint work with Stanford University. 
            
            Key contributions: multi-modal fusion, temporal reasoning, and 
            efficient attention. Code at https://github.com/mit-ai/video-transformer
            
            Questions? Contact me at jsmith@mit.edu""",
            publish_date="2024-01-01",
            duration=3600
        )
        
        metadata = extractor.extract_metadata(transcript)
        
        # Check all components extracted
        assert len(metadata['urls']) >= 1
        assert len(metadata['institutions']) >= 2
        assert len(metadata['keywords']) >= 3
        assert len(metadata['citations']) >= 2
        assert len(metadata['speakers']) >= 1
        assert len(metadata['people']) >= 1
        
        # Verify specific extractions
        assert any('github.com' in url for url in metadata['urls'])
        assert any('MIT' in inst for inst in metadata['institutions'])
        assert any('2301.00234' in cite['id'] for cite in metadata['citations'] 
                  if 'id' in cite)
    
    def test_batch_extraction(self):
        """Test batch extraction of multiple transcripts."""
        extractor = MetadataExtractor()
        
        transcripts = [
            Transcript(
                video_id=f"test_{i}",
                title=f"Lecture {i}",
                channel_name="University",
                text=f"This is lecture {i} about machine learning and AI.",
                publish_date="2024-01-01",
                duration=3600
            )
            for i in range(3)
        ]
        
        results = extractor.extract_batch(transcripts)
        
        assert len(results) == 3
        for video_id, metadata in results.items():
            assert 'keywords' in metadata
            assert 'extracted_at' in metadata


class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    def test_end_to_end_extraction(self):
        """Test complete extraction pipeline."""
        # Create a rich transcript
        transcript = Transcript(
            video_id="integration_test",
            title="Deep Learning for NLP - Stanford CS224N Lecture 10",
            channel_name="Stanford Online",
            text="""Good morning, I'm Professor Christopher Manning from Stanford's 
            NLP Group. Today's lecture covers attention mechanisms in transformers.
            
            We'll discuss the seminal paper "Attention is All You Need" by 
            Vaswani et al. (2017), available at arXiv:1706.03762. This revolutionized 
            NLP and led to BERT (Devlin et al., 2019) and GPT models.
            
            Our recent work with researchers from MIT and Google Brain extends 
            these ideas. See our paper at doi:10.1162/tacl_a_00349.
            
            Key concepts today:
            1. Self-attention mechanisms
            2. Multi-head attention
            3. Positional encodings
            4. Training transformer models
            
            For your homework, implement a basic transformer. Code templates 
            are on GitHub: https://github.com/stanford-nlp/cs224n-transformers
            
            Questions? My office hours are Tuesdays 2-4pm.""",
            publish_date="2024-01-15",
            duration=5400
        )
        
        # Extract all metadata
        metadata_extractor = MetadataExtractor()
        metadata = metadata_extractor.extract_metadata(transcript)
        
        # Verify comprehensive extraction
        assert 'Stanford' in metadata['institutions']
        assert any('1706.03762' in c.get('id', '') for c in metadata['citations'])
        assert any('github.com' in url for url in metadata['urls'])
        assert len(metadata['keywords']) >= 5
        assert any('Christopher Manning' in p for p in metadata['people'])
        
        # Test content classification
        classifier = ContentClassifier(use_ollama=False)
        classification = classifier.classify_content(transcript)
        
        assert classification.content_type == 'lecture'
        assert classification.academic_level in ['graduate', 'undergraduate']
        assert 'nlp' in classification.topics or 'machine_learning' in classification.topics
        assert classification.confidence > 0.6
        
        # Test quality indicators
        quality = classification.quality_indicators
        assert quality['academic_language'] > 0.5
        assert quality['structure_score'] > 0.5
        assert quality['citation_frequency'] > 0


if __name__ == "__main__":
    # Run basic tests
    print("Running scientific extractor tests...")
    
    # Test each component
    test_pipeline = TestScientificPipeline()
    test_pipeline.test_pipeline_initialization()
    print("✓ Pipeline initialization test passed")
    
    test_citations = TestCitationDetector()
    test_citations.test_arxiv_detection()
    print("✓ Citation detection test passed")
    
    test_speakers = TestSpeakerExtractor()
    test_speakers.test_introduction_extraction()
    print("✓ Speaker extraction test passed")
    
    test_classifier = TestContentClassifier()
    test_classifier.test_content_type_classification()
    print("✓ Content classification test passed")
    
    test_integration = TestIntegration()
    test_integration.test_end_to_end_extraction()
    print("✓ Integration test passed")
    
    print("\n✅ All scientific extractor tests passed!")