"""
Scientific content classifier using Ollama and Transformer embeddings.
Module: content_classifier.py
Description: Implementation of content classifier functionality

This module classifies YouTube transcripts into academic categories and
determines content type, academic level, and quality indicators.

External Documentation:
- Ollama: https://ollama.ai/
- Sentence Transformers: https://www.sbert.net/

Sample Input:
    Transcript with academic content

Expected Output:
    {
        'content_type': 'lecture',
        'academic_level': 'graduate',
        'topics': ['machine learning', 'neural networks'],
        'quality_score': 0.85,
        'confidence': 0.92
    }
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Try to import Ollama
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False
    ollama = None

from src.youtube_transcripts.core.models import Transcript
from src.youtube_transcripts.core.utils.embedding_wrapper import EmbeddingUtils

logger = logging.getLogger(__name__)


@dataclass
class ContentClassification:
    """Represents content classification results."""
    content_type: str  # lecture, tutorial, conference, demo, discussion
    academic_level: str  # undergraduate, graduate, research, professional
    primary_topic: str  # Main subject area
    topics: list[str]  # All identified topics
    quality_indicators: dict[str, float]  # Various quality metrics
    confidence: float  # Overall confidence in classification


class ContentClassifier:
    """Classify academic content using NLP and embeddings."""

    # Content type indicators
    CONTENT_TYPE_INDICATORS = {
        'lecture': [
            'today we will', 'in this lecture', 'welcome to class',
            'last time we', 'homework', 'assignment', 'syllabus',
            'midterm', 'final exam', 'office hours'
        ],
        'tutorial': [
            'how to', 'step by step', 'tutorial', 'getting started',
            'installation', 'setup', 'example code', 'demo code',
            "let's build", "we'll implement"
        ],
        'conference': [
            'conference', 'symposium', 'workshop', 'keynote',
            'presentation', 'talk', 'session', 'q&a', 'questions from audience',
            'thank you for inviting'
        ],
        'demo': [
            'demonstration', 'demo', "let me show", "you can see",
            'live coding', 'real-time', 'running example',
            'output shows', 'results show'
        ],
        'discussion': [
            'panel', 'discussion', 'debate', 'conversation',
            'interview', 'thoughts on', 'opinion', 'perspective',
            'agree', 'disagree'
        ]
    }

    # Academic level indicators
    LEVEL_INDICATORS = {
        'undergraduate': [
            'intro to', 'introduction', 'basics', 'fundamentals',
            '101', 'beginner', 'first course', 'prerequisite',
            'no prior knowledge', 'simple example'
        ],
        'graduate': [
            'advanced', 'graduate', 'masters', 'phd', 'research methods',
            'literature review', 'thesis', 'dissertation',
            'seminar', 'deep dive'
        ],
        'research': [
            'our paper', 'we propose', 'novel approach', 'contribution',
            'evaluation', 'experiments show', 'baseline',
            'state-of-the-art', 'future work', 'limitations'
        ],
        'professional': [
            'industry', 'production', 'real-world', 'case study',
            'best practices', 'lessons learned', 'deployment',
            'scale', 'performance', 'cost'
        ]
    }

    # Topic categories
    TOPIC_KEYWORDS = {
        'machine_learning': [
            'machine learning', 'neural network', 'deep learning',
            'training', 'model', 'dataset', 'accuracy', 'loss',
            'gradient', 'backpropagation', 'optimization'
        ],
        'computer_vision': [
            'computer vision', 'image', 'video', 'convolution',
            'object detection', 'segmentation', 'recognition',
            'pixel', 'feature extraction', 'cv'
        ],
        'nlp': [
            'natural language', 'nlp', 'text', 'language model',
            'tokenization', 'embedding', 'transformer', 'bert',
            'gpt', 'attention', 'sequence'
        ],
        'reinforcement_learning': [
            'reinforcement learning', 'rl', 'agent', 'environment',
            'reward', 'policy', 'q-learning', 'actor-critic',
            'exploration', 'exploitation'
        ],
        'robotics': [
            'robot', 'robotics', 'control', 'sensor', 'actuator',
            'kinematics', 'dynamics', 'manipulation', 'navigation',
            'slam', 'perception'
        ],
        'theory': [
            'algorithm', 'complexity', 'proof', 'theorem',
            'computational', 'optimization', 'convergence',
            'bound', 'analysis', 'theoretical'
        ]
    }

    def __init__(self, use_ollama: bool = True,
                 ollama_model: str = "qwen2.5:3b"):
        """Initialize the content classifier.
        
        Args:
            use_ollama: Whether to use Ollama for classification
            ollama_model: Ollama model to use
        """
        self.embedding_utils = EmbeddingUtils()
        self.use_ollama = use_ollama and HAS_OLLAMA
        self.ollama_model = ollama_model

        if self.use_ollama and not HAS_OLLAMA:
            logger.warning("Ollama requested but not available")

        # Precompute embeddings for topic keywords
        self._init_topic_embeddings()

    def _init_topic_embeddings(self):
        """Initialize embeddings for topic classification."""
        self.topic_embeddings = {}

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            # Combine keywords into representative text
            text = ' '.join(keywords)
            embedding = self.embedding_utils.generate_embeddings([text])[0]
            self.topic_embeddings[topic] = embedding

    def classify_content(self, transcript: Transcript) -> ContentClassification:
        """Classify a transcript's content.
        
        Args:
            transcript: Transcript object to classify
            
        Returns:
            ContentClassification object
        """
        text = transcript.text.lower()

        # Determine content type
        content_type, type_confidence = self._classify_content_type(text)

        # Determine academic level
        academic_level, level_confidence = self._classify_academic_level(text)

        # Extract topics
        topics, topic_scores = self._extract_topics(transcript)
        primary_topic = topics[0] if topics else 'general'

        # Calculate quality indicators
        quality_indicators = self._calculate_quality_indicators(transcript)

        # Use Ollama for more nuanced classification if available
        if self.use_ollama:
            ollama_result = self._classify_with_ollama(transcript.text[:2000])
            if ollama_result:
                # Merge Ollama results with rule-based results
                content_type = ollama_result.get('content_type', content_type)
                academic_level = ollama_result.get('level', academic_level)

        # Calculate overall confidence
        confidence = np.mean([type_confidence, level_confidence,
                             max(topic_scores.values()) if topic_scores else 0.5])

        return ContentClassification(
            content_type=content_type,
            academic_level=academic_level,
            primary_topic=primary_topic,
            topics=topics,
            quality_indicators=quality_indicators,
            confidence=float(confidence)
        )

    def _classify_content_type(self, text: str) -> tuple[str, float]:
        """Classify the content type based on indicators."""
        scores = {}

        for content_type, indicators in self.CONTENT_TYPE_INDICATORS.items():
            score = 0
            for indicator in indicators:
                if indicator in text:
                    score += 1
            scores[content_type] = score

        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            for content_type in scores:
                scores[content_type] /= total

        # Get best match
        if scores:
            best_type = max(scores, key=scores.get)
            confidence = scores[best_type]

            # Default to lecture if confidence is low
            if confidence < 0.2:
                return 'lecture', 0.5

            return best_type, confidence

        return 'lecture', 0.5

    def _classify_academic_level(self, text: str) -> tuple[str, float]:
        """Classify the academic level."""
        scores = {}

        for level, indicators in self.LEVEL_INDICATORS.items():
            score = 0
            for indicator in indicators:
                if indicator in text:
                    score += 1
            scores[level] = score

        # Check for specific patterns
        if re.search(r'\b\d{3}\b', text):  # Course numbers
            match = re.search(r'\b(\d{3})\b', text)
            if match:
                number = int(match.group(1))
                if number < 300:
                    scores['undergraduate'] += 2
                elif number < 500:
                    scores['undergraduate'] += 1
                else:
                    scores['graduate'] += 2

        # Normalize and get best match
        total = sum(scores.values())
        if total > 0:
            for level in scores:
                scores[level] /= total

            best_level = max(scores, key=scores.get)
            return best_level, scores[best_level]

        return 'undergraduate', 0.5

    def _extract_topics(self, transcript: Transcript) -> tuple[list[str], dict[str, float]]:
        """Extract topics using embeddings and keyword matching."""
        # Generate embedding for transcript
        text_embedding = self.embedding_utils.generate_embeddings([transcript.text[:5000]])[0]

        # Calculate similarity with topic embeddings
        topic_scores = {}
        for topic, topic_embedding in self.topic_embeddings.items():
            similarity = cosine_similarity(
                [text_embedding],
                [topic_embedding]
            )[0][0]
            topic_scores[topic] = float(similarity)

        # Also count keyword occurrences
        text_lower = transcript.text.lower()
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            keyword_score = 0
            for keyword in keywords:
                keyword_score += text_lower.count(keyword)

            # Combine embedding similarity and keyword count
            if topic in topic_scores:
                topic_scores[topic] = (topic_scores[topic] +
                                      min(keyword_score / 100, 1.0)) / 2

        # Sort topics by score
        sorted_topics = sorted(topic_scores.items(),
                              key=lambda x: x[1], reverse=True)

        # Return top topics with significant scores
        topics = [topic for topic, score in sorted_topics if score > 0.3]

        return topics[:5], topic_scores

    def _calculate_quality_indicators(self, transcript: Transcript) -> dict[str, float]:
        """Calculate various quality indicators."""
        text = transcript.text
        words = text.split()
        sentences = text.split('.')

        indicators = {}

        # Technical density (technical terms per 100 words)
        technical_terms = sum(1 for word in words
                             if self._is_technical_term(word))
        indicators['technical_density'] = min(technical_terms / len(words) * 100, 1.0)

        # Citation frequency
        citation_count = (text.count('et al') + text.count('arXiv') +
                         text.count('doi:') + len(re.findall(r'\(\d{4}\)', text)))
        indicators['citation_frequency'] = min(citation_count / len(sentences) * 10, 1.0)

        # Structure score (sections, numbering, etc.)
        structure_markers = len(re.findall(
            r'(?:first|second|third|next|finally|introduction|conclusion|'
            r'section \d+|part \d+|\d+\.|agenda|outline)',
            text, re.IGNORECASE
        ))
        indicators['structure_score'] = min(structure_markers / 20, 1.0)

        # Academic language score
        academic_phrases = [
            'research', 'study', 'analysis', 'hypothesis', 'methodology',
            'results show', 'we found', 'evidence suggests', 'literature',
            'theoretical', 'empirical', 'significant'
        ]
        academic_count = sum(1 for phrase in academic_phrases
                           if phrase in text.lower())
        indicators['academic_language'] = min(academic_count / 15, 1.0)

        # Length indicator (longer usually means more comprehensive)
        indicators['comprehensiveness'] = min(len(words) / 5000, 1.0)

        return indicators

    def _is_technical_term(self, word: str) -> bool:
        """Check if a word is likely a technical term."""
        word = word.lower().strip('.,!?;:()')

        # Check if it's an acronym
        if word.isupper() and len(word) >= 2:
            return True

        # Check if it contains numbers
        if any(char.isdigit() for char in word):
            return True

        # Check against technical term patterns
        technical_patterns = [
            r'-based$', r'^pre-', r'^post-', r'^multi-',
            r'^cross-', r'^self-', r'^co-', r'ization$',
            r'isation$', r'ometry$', r'ology$'
        ]

        for pattern in technical_patterns:
            if re.search(pattern, word):
                return True

        # Check if it's in any topic keywords
        for keywords in self.TOPIC_KEYWORDS.values():
            if word in ' '.join(keywords).lower().split():
                return True

        return False

    def _classify_with_ollama(self, text_sample: str) -> dict[str, Any] | None:
        """Use Ollama for advanced content classification."""
        if not self.use_ollama:
            return None

        try:
            prompt = f"""Analyze this academic transcript excerpt and classify it.
            
            Determine:
            1. Content type: lecture, tutorial, conference, demo, or discussion
            2. Academic level: undergraduate, graduate, research, or professional
            3. Main topics covered
            4. Quality indicators
            
            Text: {text_sample}
            
            Return a JSON object with: content_type, level, topics (list), quality (0-1)"""

            response = ollama.generate(
                model=self.ollama_model,
                prompt=prompt
            )

            # Parse response
            try:
                response_text = response['response']
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Failed to parse Ollama response: {e}")

            return None

        except Exception as e:
            logger.error(f"Ollama classification failed: {e}")
            return None

    def batch_classify(self, transcripts: list[Transcript]) -> list[ContentClassification]:
        """Classify multiple transcripts.
        
        Args:
            transcripts: List of transcripts to classify
            
        Returns:
            List of classifications
        """
        classifications = []

        for transcript in transcripts:
            try:
                classification = self.classify_content(transcript)
                classifications.append(classification)
            except Exception as e:
                logger.error(f"Failed to classify transcript {transcript.video_id}: {e}")
                # Add default classification on error
                classifications.append(ContentClassification(
                    content_type='unknown',
                    academic_level='unknown',
                    primary_topic='unknown',
                    topics=[],
                    quality_indicators={},
                    confidence=0.0
                ))

        return classifications


if __name__ == "__main__":
    # Test the content classifier
    classifier = ContentClassifier(use_ollama=False)  # Disable Ollama for testing

    # Create test transcripts
    test_transcripts = [
        Transcript(
            video_id="test_001",
            title="Introduction to Machine Learning - Lecture 1",
            channel_name="MIT OpenCourseWare",
            text="""Welcome to Introduction to Machine Learning, course 6.034.
            Today we'll cover the basics of supervised learning. First, let's 
            review what we learned last week about probability. For homework,
            you'll implement a simple neural network. Remember, office hours
            are Tuesdays at 3pm.""",
            publish_date="2024-01-15",
            duration=3600
        ),

        Transcript(
            video_id="test_002",
            title="Building a GPT Model from Scratch - Tutorial",
            channel_name="AI Tutorial Channel",
            text="""In this tutorial, I'll show you how to build a GPT model
            step by step. First, let's install the required packages. We'll
            use PyTorch for this demo. Let me show you the code. You can see
            the output here. The complete code is available on GitHub.""",
            publish_date="2024-01-16",
            duration=1800
        ),

        Transcript(
            video_id="test_003",
            title="VERL: A New Framework for Video Understanding - NeurIPS 2023",
            channel_name="Conference Talks",
            text="""Thank you for inviting me to present our paper at NeurIPS.
            We propose VERL, a novel approach for video understanding. Our
            experiments show state-of-the-art results on ActivityNet. This
            builds on prior work by Smith et al. (2022) and uses techniques
            from Johnson (2021). Future work includes scaling to longer videos.
            Any questions from the audience?""",
            publish_date="2024-01-17",
            duration=2400
        )
    ]

    print("=== Content Classification Test ===\n")

    for transcript in test_transcripts:
        print(f"Video: {transcript.title}")
        print(f"Channel: {transcript.channel_name}\n")

        classification = classifier.classify_content(transcript)

        print("Classification Results:")
        print(f"  Content Type: {classification.content_type}")
        print(f"  Academic Level: {classification.academic_level}")
        print(f"  Primary Topic: {classification.primary_topic}")
        print(f"  All Topics: {', '.join(classification.topics)}")
        print(f"  Confidence: {classification.confidence:.2%}")
        print("\nQuality Indicators:")
        for indicator, score in classification.quality_indicators.items():
            print(f"  {indicator}: {score:.2f}")
        print("\n" + "="*50 + "\n")

    print("✓ Content classification test complete!")
