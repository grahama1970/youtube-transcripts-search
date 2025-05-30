"""
Speaker extraction using SpaCy NER and dependency parsing.

This module extracts speaker information including names, titles, and 
affiliations from YouTube transcripts using advanced NLP techniques.

External Documentation:
- SpaCy NER: https://spacy.io/usage/linguistic-features#named-entities
- SpaCy Dependencies: https://spacy.io/usage/linguistic-features#dependency-parse

Sample Input:
    "Hello, I'm Dr. Sarah Johnson from MIT's Computer Science department.
    Today we have Professor Chen from Stanford joining us."

Expected Output:
    [
        {
            'name': 'Dr. Sarah Johnson',
            'title': 'Dr.',
            'affiliation': 'MIT',
            'department': 'Computer Science',
            'timestamp': '00:00:00'
        },
        {
            'name': 'Professor Chen',
            'title': 'Professor',
            'affiliation': 'Stanford',
            'timestamp': '00:00:05'
        }
    ]
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import logging

import spacy
from spacy.tokens import Doc, Token, Span
from spacy.matcher import Matcher, PhraseMatcher

logger = logging.getLogger(__name__)


@dataclass
class Speaker:
    """Represents an identified speaker."""
    name: str
    title: Optional[str] = None
    affiliation: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None  # speaker, moderator, panelist, etc.
    timestamp: Optional[str] = None
    confidence: float = 1.0


class SpeakerExtractor:
    """Extract speaker information using SpaCy NER and patterns."""
    
    # Academic and professional titles
    TITLES = {
        'academic': {
            'dr', 'doctor', 'professor', 'prof', 'associate professor',
            'assistant professor', 'lecturer', 'instructor', 'dean',
            'president', 'provost', 'chair', 'director'
        },
        'research': {
            'researcher', 'scientist', 'postdoc', 'postdoctoral',
            'phd student', 'graduate student', 'research fellow',
            'principal investigator', 'pi'
        },
        'professional': {
            'ceo', 'cto', 'founder', 'co-founder', 'engineer',
            'manager', 'lead', 'head', 'vp', 'vice president'
        }
    }
    
    # Introduction patterns
    INTRO_PATTERNS = [
        r"(?:i am|i'm|my name is)\s+([^,.]+?)(?:\s+from\s+(.+?))?[,.]",
        r"(?:this is|here's|we have)\s+([^,.]+?)(?:\s+from\s+(.+?))?[,.]",
        r"(?:joining us|with us today|our speaker)\s+(?:is\s+)?([^,.]+?)(?:\s+from\s+(.+?))?[,.]",
        r"([^,.]+?)\s+(?:from|at|with)\s+([^,.]+?)(?:\s+is\s+(?:here|joining|speaking))",
    ]
    
    def __init__(self, spacy_model: str = "en_core_web_sm"):
        """Initialize the speaker extractor.
        
        Args:
            spacy_model: SpaCy model to use
        """
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", spacy_model], check=True)
            self.nlp = spacy.load(spacy_model)
        
        # Initialize matchers
        self.matcher = Matcher(self.nlp.vocab)
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize SpaCy patterns for speaker detection."""
        
        # Add title patterns to phrase matcher
        all_titles = []
        for title_set in self.TITLES.values():
            all_titles.extend(title_set)
        
        title_patterns = [self.nlp.make_doc(title) for title in all_titles]
        self.phrase_matcher.add("TITLE", title_patterns)
        
        # Pattern: [Title] [Name] from [Organization]
        title_name_org = [
            {"POS": {"IN": ["PROPN", "NOUN"]}, "OP": "?"},  # Optional title
            {"ENT_TYPE": "PERSON"},  # Person entity
            {"TEXT": {"IN": ["from", "at", "with"]}, "OP": "?"},
            {"ENT_TYPE": "ORG", "OP": "?"}  # Organization
        ]
        self.matcher.add("SPEAKER_PATTERN", [title_name_org])
    
    def extract_speakers(self, text: str, 
                        timestamps: Optional[List[str]] = None) -> List[Speaker]:
        """Extract all speakers from the text.
        
        Args:
            text: Transcript text
            timestamps: Optional list of timestamps corresponding to text segments
            
        Returns:
            List of identified speakers
        """
        doc = self.nlp(text)
        speakers = []
        
        # Method 1: Extract from introductions
        speakers.extend(self._extract_from_introductions(text, doc))
        
        # Method 2: Extract from entity patterns
        speakers.extend(self._extract_from_entities(doc))
        
        # Method 3: Extract from speaker labels
        speakers.extend(self._extract_from_labels(text))
        
        # Deduplicate and merge speaker information
        speakers = self._merge_speakers(speakers)
        
        # Add timestamps if provided
        if timestamps:
            self._add_timestamps(speakers, text, timestamps)
        
        return speakers
    
    def _extract_from_introductions(self, text: str, doc: Doc) -> List[Speaker]:
        """Extract speakers from introduction patterns."""
        speakers = []
        
        for pattern in self.INTRO_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1).strip()
                affiliation = match.group(2).strip() if match.lastindex >= 2 else None
                
                # Process name to extract title
                name_doc = self.nlp(name)
                title = None
                clean_name = name
                
                # Check for titles in the name
                title_matches = self.phrase_matcher(name_doc)
                if title_matches:
                    for match_id, start, end in title_matches:
                        title = name_doc[start:end].text
                        # Remove title from name
                        clean_name = name.replace(title, "").strip()
                
                # Verify it's a person
                if self._is_likely_person(clean_name):
                    speaker = Speaker(
                        name=clean_name,
                        title=title,
                        affiliation=affiliation
                    )
                    speakers.append(speaker)
        
        return speakers
    
    def _extract_from_entities(self, doc: Doc) -> List[Speaker]:
        """Extract speakers from named entities and their context."""
        speakers = []
        
        # Look for PERSON entities
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                speaker = Speaker(name=ent.text)
                
                # Look for title before the name
                if ent.start > 0:
                    prev_tokens = doc[max(0, ent.start - 3):ent.start]
                    for token in reversed(prev_tokens):
                        if token.text.lower() in self._flatten_titles():
                            speaker.title = token.text
                            break
                
                # Look for affiliation after the name
                if ent.end < len(doc) - 3:
                    next_tokens = doc[ent.end:min(len(doc), ent.end + 5)]
                    for i, token in enumerate(next_tokens):
                        if token.text.lower() in ["from", "at", "with", "of"]:
                            # Look for organization
                            for org_ent in doc.ents:
                                if (org_ent.label_ == "ORG" and 
                                    org_ent.start >= ent.end + i):
                                    speaker.affiliation = org_ent.text
                                    break
                            break
                
                # Check if this is a valid speaker
                if self._is_likely_speaker(speaker, doc):
                    speakers.append(speaker)
        
        return speakers
    
    def _extract_from_labels(self, text: str) -> List[Speaker]:
        """Extract speakers from explicit labels like 'Speaker:', 'Moderator:'."""
        speakers = []
        
        # Pattern for labeled speakers
        label_pattern = re.compile(
            r'(?:^|\n)\s*(?P<role>Speaker|Moderator|Panelist|Host|Guest|Presenter)'
            r'\s*(?:\d+)?\s*:\s*(?P<name>[^\n]+?)(?:\n|$)',
            re.IGNORECASE | re.MULTILINE
        )
        
        for match in label_pattern.finditer(text):
            role = match.group('role').lower()
            name_text = match.group('name').strip()
            
            # Process the name
            name_doc = self.nlp(name_text)
            
            # Extract person entity from the name text
            for ent in name_doc.ents:
                if ent.label_ == "PERSON":
                    speaker = Speaker(
                        name=ent.text,
                        role=role
                    )
                    
                    # Look for affiliation in the same line
                    for org_ent in name_doc.ents:
                        if org_ent.label_ == "ORG":
                            speaker.affiliation = org_ent.text
                    
                    speakers.append(speaker)
                    break
            else:
                # No entity found, try to extract name manually
                words = name_text.split()
                if 2 <= len(words) <= 4:  # Reasonable name length
                    speaker = Speaker(
                        name=name_text,
                        role=role,
                        confidence=0.7  # Lower confidence
                    )
                    speakers.append(speaker)
        
        return speakers
    
    def _is_likely_person(self, name: str) -> bool:
        """Check if a string is likely a person's name."""
        if not name or len(name) < 3:
            return False
        
        # Check for reasonable length
        words = name.split()
        if len(words) < 1 or len(words) > 5:
            return False
        
        # Check if words are capitalized (common for names)
        if not all(word[0].isupper() for word in words if word):
            return False
        
        # Avoid common false positives
        false_positives = {
            'abstract', 'introduction', 'conclusion', 'overview',
            'summary', 'outline', 'agenda', 'schedule'
        }
        if name.lower() in false_positives:
            return False
        
        return True
    
    def _is_likely_speaker(self, speaker: Speaker, doc: Doc) -> bool:
        """Check if an extracted entity is likely a speaker."""
        # Must have a valid name
        if not self._is_likely_person(speaker.name):
            return False
        
        # Boost confidence if has title or affiliation
        if speaker.title or speaker.affiliation:
            return True
        
        # Check context for speaker indicators
        name_idx = doc.text.lower().find(speaker.name.lower())
        if name_idx > 0:
            context = doc.text[max(0, name_idx - 50):name_idx + 50].lower()
            speaker_indicators = [
                'welcome', 'introduce', 'speaker', 'presenting',
                'joining us', 'with us', 'thank you', 'questions'
            ]
            if any(indicator in context for indicator in speaker_indicators):
                return True
        
        return speaker.confidence > 0.5
    
    def _flatten_titles(self) -> Set[str]:
        """Get all titles as a flat set."""
        all_titles = set()
        for title_set in self.TITLES.values():
            all_titles.update(title_set)
        return all_titles
    
    def _merge_speakers(self, speakers: List[Speaker]) -> List[Speaker]:
        """Merge duplicate speakers and combine their information."""
        merged = {}
        
        for speaker in speakers:
            # Create a key for matching (normalized name)
            key = self._normalize_name(speaker.name)
            
            if key not in merged:
                merged[key] = speaker
            else:
                # Merge information
                existing = merged[key]
                if not existing.title and speaker.title:
                    existing.title = speaker.title
                if not existing.affiliation and speaker.affiliation:
                    existing.affiliation = speaker.affiliation
                if not existing.department and speaker.department:
                    existing.department = speaker.department
                if not existing.role and speaker.role:
                    existing.role = speaker.role
                # Keep higher confidence
                existing.confidence = max(existing.confidence, speaker.confidence)
        
        return list(merged.values())
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Remove titles
        for title in self._flatten_titles():
            name = re.sub(rf'\b{title}\b\.?', '', name, flags=re.IGNORECASE)
        
        # Remove extra whitespace and lowercase
        return ' '.join(name.lower().split())
    
    def _add_timestamps(self, speakers: List[Speaker], text: str, 
                       timestamps: List[str]) -> None:
        """Add timestamps to speakers based on their first mention."""
        for speaker in speakers:
            # Find first occurrence of speaker name
            idx = text.lower().find(speaker.name.lower())
            if idx >= 0:
                # Find corresponding timestamp
                # This is a simplified approach - in practice you'd need
                # proper alignment between text and timestamps
                position_ratio = idx / len(text)
                timestamp_idx = int(position_ratio * len(timestamps))
                if timestamp_idx < len(timestamps):
                    speaker.timestamp = timestamps[timestamp_idx]
    
    def format_speakers(self, speakers: List[Speaker], 
                       format: str = 'json') -> str:
        """Format speakers for output.
        
        Args:
            speakers: List of speakers
            format: Output format ('json', 'markdown', 'text')
            
        Returns:
            Formatted string
        """
        if format == 'json':
            import json
            return json.dumps([asdict(s) for s in speakers], indent=2)
        
        elif format == 'markdown':
            lines = ["# Speakers\n"]
            for speaker in speakers:
                line = f"- **{speaker.name}**"
                if speaker.title:
                    line = f"- **{speaker.title} {speaker.name}**"
                if speaker.affiliation:
                    line += f" ({speaker.affiliation})"
                if speaker.role:
                    line += f" - *{speaker.role}*"
                lines.append(line)
            return '\n'.join(lines)
        
        elif format == 'text':
            lines = []
            for speaker in speakers:
                parts = []
                if speaker.title:
                    parts.append(speaker.title)
                parts.append(speaker.name)
                if speaker.affiliation:
                    parts.append(f"from {speaker.affiliation}")
                if speaker.role:
                    parts.append(f"({speaker.role})")
                lines.append(' '.join(parts))
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unknown format: {format}")


if __name__ == "__main__":
    # Test the speaker extractor
    extractor = SpeakerExtractor()
    
    test_texts = [
        """Good morning everyone. I'm Professor Jane Smith from MIT's Computer Science 
        department. Today we have a special guest, Dr. Robert Chen from Stanford 
        University, who will be talking about machine learning.
        
        Moderator: Sarah Johnson, Director of AI Research at Google
        
        Let me also introduce our panelists: Professor Liu from Berkeley and 
        Dr. Patel from Microsoft Research.""",
        
        """Welcome to our conference. This is John Davis, and I'll be your host today.
        Our keynote speaker is Professor Emily Watson from Harvard Medical School.
        She'll be joined by Dr. Michael Brown from Johns Hopkins.""",
        
        """Speaker 1: Dr. Alice Cooper (University of Chicago)
        Speaker 2: Bob Wilson, CEO of TechCorp
        
        Alice: Thank you for having me. As a researcher at Chicago...
        Bob: It's great to be here. At TechCorp, we've been working on..."""
    ]
    
    print("=== Speaker Extraction Test ===\n")
    
    for i, text in enumerate(test_texts, 1):
        print(f"Test {i}:")
        print(f"Text preview: {text[:100]}...\n")
        
        speakers = extractor.extract_speakers(text)
        
        print(f"Found {len(speakers)} speakers:")
        for speaker in speakers:
            print(f"  - Name: {speaker.name}")
            if speaker.title:
                print(f"    Title: {speaker.title}")
            if speaker.affiliation:
                print(f"    Affiliation: {speaker.affiliation}")
            if speaker.role:
                print(f"    Role: {speaker.role}")
            print(f"    Confidence: {speaker.confidence:.2f}")
            print()
        
        # Test formatting
        print("Markdown format:")
        print(extractor.format_speakers(speakers, 'markdown'))
        print("\n" + "="*50 + "\n")
    
    print("✓ Speaker extraction test complete!")