#!/usr/bin/env python3
"""
Module: link_extractor.py
Description: Extract and categorize GitHub and arXiv links from text with attribution

External Dependencies:
- linkify-it-py: https://pypi.org/project/linkify-it-py/
- validators: https://pypi.org/project/validators/
- loguru: https://pypi.org/project/loguru/

Sample Input:
>>> text = "Check out https://github.com/openai/gpt-4 and arXiv:2301.12345"
>>> extract_links_from_text(text, "video_author", True)

Expected Output:
>>> [ExtractedLink(url='https://github.com/openai/gpt-4', link_type='github', source='video_author', is_authoritative=True),
     ExtractedLink(url='https://arxiv.org/abs/2301.12345', link_type='arxiv', source='video_author', is_authoritative=True)]

Example Usage:
>>> from link_extractor import extract_links_from_text, ExtractedLink
>>> links = extract_links_from_text("See github.com/pytorch/pytorch", "commenter")
"""

import re
from dataclasses import dataclass
from typing import List

from linkify_it import LinkifyIt
from loguru import logger


@dataclass
class ExtractedLink:
    """Represents an extracted link with metadata."""
    url: str
    link_type: str  # 'github' or 'arxiv'
    source: str  # 'video_author' or comment author name
    is_authoritative: bool  # True if from video author


def extract_links_from_text(text: str, source: str, is_authoritative: bool = False) -> List[ExtractedLink]:
    """
    Extract GitHub repository links and arXiv paper links from text using linkify-it.
    
    Args:
        text: Text to extract links from
        source: Source of the text (e.g., 'video_author' or commenter name)
        is_authoritative: Whether this is from the video author
        
    Returns:
        List of ExtractedLink objects
    """
    # Initialize linkify-it
    linkify = LinkifyIt()
    
    # Find all links
    matches = linkify.match(text) or []
    
    extracted_links = []
    seen_urls = set()  # To avoid duplicates
    
    for match in matches:
        url = match.url
        
        # Normalize GitHub URLs to just owner/repo
        github_match = re.match(r'https?://github\.com/([\w-]+/[\w.-]+)', url, re.IGNORECASE)
        if github_match:
            canonical_url = f'https://github.com/{github_match.group(1)}'
            if canonical_url not in seen_urls:
                seen_urls.add(canonical_url)
                extracted_links.append(ExtractedLink(
                    url=canonical_url,
                    link_type='github',
                    source=source,
                    is_authoritative=is_authoritative
                ))
            continue
        
        # Check for arXiv links
        if 'arxiv.org' in url.lower():
            # Normalize to abs URL if it's a PDF link
            url = url.replace('/pdf/', '/abs/')
            # Ensure HTTPS
            if url.startswith('http://'):
                url = url.replace('http://', 'https://')
            if url not in seen_urls:
                seen_urls.add(url)
                extracted_links.append(ExtractedLink(
                    url=url,
                    link_type='arxiv',
                    source=source,
                    is_authoritative=is_authoritative
                ))
            continue
    
    # Also check for arXiv:XXXX.XXXX format
    arxiv_pattern = r'arXiv:\s*(\d+\.\d+(?:v\d+)?)'
    for match in re.finditer(arxiv_pattern, text, re.IGNORECASE):
        arxiv_id = match.group(1)
        arxiv_url = f'https://arxiv.org/abs/{arxiv_id}'
        if arxiv_url not in seen_urls:
            seen_urls.add(arxiv_url)
            extracted_links.append(ExtractedLink(
                url=arxiv_url,
                link_type='arxiv',
                source=source,
                is_authoritative=is_authoritative
            ))
    
    return extracted_links


def categorize_links(links: List[ExtractedLink]) -> dict:
    """
    Categorize links by type and authoritativeness.
    
    Args:
        links: List of ExtractedLink objects
        
    Returns:
        Dictionary with categorized links
    """
    return {
        'github_authoritative': [l for l in links if l.link_type == 'github' and l.is_authoritative],
        'github_community': [l for l in links if l.link_type == 'github' and not l.is_authoritative],
        'arxiv_authoritative': [l for l in links if l.link_type == 'arxiv' and l.is_authoritative],
        'arxiv_community': [l for l in links if l.link_type == 'arxiv' and not l.is_authoritative],
    }


if __name__ == "__main__":
    # Test the module
    test_text = """
    Check out the implementation at https://github.com/openai/whisper
    Based on the paper: arXiv:2212.04356
    
    Also see github.com/pytorch/pytorch for the framework.
    Related work: https://arxiv.org/abs/2301.12345
    """
    
    links = extract_links_from_text(test_text, "test_author", is_authoritative=True)
    
    print("Extracted links:")
    for link in links:
        print(f"  - {link.url} ({link.link_type}, authoritative={link.is_authoritative})")
    
    categorized = categorize_links(links)
    print("\nCategorized:")
    for category, items in categorized.items():
        if items:
            print(f"  {category}: {len(items)} links")
    
    print("✅ Module validation passed")