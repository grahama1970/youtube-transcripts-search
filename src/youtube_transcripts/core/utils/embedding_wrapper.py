"""
Wrapper for embedding utilities to provide a consistent interface.
Module: embedding_wrapper.py
Description: Implementation of embedding wrapper functionality

This module wraps the embedding functions in a class for easier use
throughout the application.
"""

import hashlib

import numpy as np


def generate_embedding(text: str) -> np.ndarray:
    """Generate a simple embedding for text.
    
    This is a fallback implementation that creates a deterministic
    embedding based on the text content.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector
    """
    # Create a hash of the text
    text_hash = hashlib.sha256(text.encode()).hexdigest()

    # Convert hash to numbers
    numbers = []
    for i in range(0, len(text_hash), 2):
        numbers.append(int(text_hash[i:i+2], 16) / 255.0)

    # Pad or truncate to 384 dimensions (typical for sentence transformers)
    embedding = np.array(numbers[:384])
    if len(embedding) < 384:
        embedding = np.pad(embedding, (0, 384 - len(embedding)), mode='constant')

    # Add some text-based features
    embedding[0] = len(text) / 1000.0  # Text length feature
    embedding[1] = text.count(' ') / 100.0  # Word count approximation

    # Normalize
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding


class EmbeddingUtils:
    """Utility class for generating embeddings."""

    def __init__(self):
        """Initialize embedding utilities."""
        pass

    def generate_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
