#!/usr/bin/env python3
"""
Simple test of scientific extractors without pytest complexity.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.youtube_transcripts.core.models import Transcript
from src.youtube_transcripts.core.utils.spacy_scientific import ScientificPipeline

def test_basic_extraction():
    """Test basic extraction functionality."""
    print("Testing SpaCy Scientific Pipeline...")
    
    # Create pipeline
    pipeline = ScientificPipeline()
    
    # Test text
    text = """Professor Jane Smith from MIT presented work on transformers. 
    See arXiv:2301.00234 and Devlin et al. (2019) for background."""
    
    # Process text
    results = pipeline.process_transcript(text)
    
    print(f"\nExtracted:")
    print(f"  People: {results['people']}")
    print(f"  Institutions: {results['institutions']}")
    print(f"  Citations: {len(results['citations'])} found")
    print(f"  Technical terms: {len(results['technical_terms'])} found")
    
    # Verify results
    assert len(results['people']) >= 1
    assert 'MIT' in str(results['institutions'])
    assert len(results['citations']) >= 1  # At least one citation
    
    print("\n✅ Basic extraction test passed!")
    return True

def test_citation_detector():
    """Test citation detection."""
    print("\nTesting Citation Detector...")
    
    from src.youtube_transcripts.citation_detector import CitationDetector
    
    detector = CitationDetector(use_ollama=False)
    
    text = "See arXiv:2301.00234 and doi:10.1038/nature12373"
    citations = detector.detect_citations(text)
    
    print(f"  Found {len(citations)} citations")
    for c in citations:
        print(f"    - {c.type}: {c.id or c.text}")
    
    assert len(citations) >= 2
    print("✅ Citation detection test passed!")
    return True

def test_speaker_extractor():
    """Test speaker extraction."""
    print("\nTesting Speaker Extractor...")
    
    from src.youtube_transcripts.speaker_extractor import SpeakerExtractor
    
    extractor = SpeakerExtractor()
    
    text = "I'm Professor Smith from Harvard. Dr. Jones from MIT will present next."
    speakers = extractor.extract_speakers(text)
    
    print(f"  Found {len(speakers)} speakers")
    for s in speakers:
        print(f"    - {s.name} ({s.affiliation})")
    
    assert len(speakers) >= 2
    print("✅ Speaker extraction test passed!")
    return True

def test_content_classifier():
    """Test content classification."""
    print("\nTesting Content Classifier...")
    
    from src.youtube_transcripts.content_classifier import ContentClassifier
    
    classifier = ContentClassifier(use_ollama=False)
    
    transcript = Transcript(
        video_id="test",
        title="Machine Learning Lecture",
        channel_name="University",
        text="Welcome to class. Today we'll learn about neural networks.",
        publish_date="2024-01-01",
        duration=3600
    )
    
    result = classifier.classify_content(transcript)
    
    print(f"  Content type: {result.content_type}")
    print(f"  Academic level: {result.academic_level}")
    print(f"  Confidence: {result.confidence:.2%}")
    
    assert result.content_type in ['lecture', 'tutorial', 'conference']
    print("✅ Content classification test passed!")
    return True

def main():
    """Run all tests."""
    print("=== Running Scientific Extractor Tests ===\n")
    
    tests = [
        test_basic_extraction,
        test_citation_detector,
        test_speaker_extractor,
        test_content_classifier
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\n=== Summary ===")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)