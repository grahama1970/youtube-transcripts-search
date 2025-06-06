"""
Data models for YouTube transcripts.
Module: models.py
Description: Data models and schemas for models

This module defines the core data structures used throughout the application.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Transcript:
    """Represents a YouTube video transcript with metadata."""

    video_id: str
    title: str
    channel_name: str
    text: str  # The actual transcript text
    publish_date: str  # ISO format date string
    duration: int  # Duration in seconds

    # Optional fields
    summary: str | None = None
    enhanced_transcript: str | None = None
    metadata: dict[str, Any] | None = None

    @property
    def url(self) -> str:
        """Get the YouTube URL for this video."""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def publish_datetime(self) -> datetime:
        """Get publish date as datetime object."""
        return datetime.fromisoformat(self.publish_date.replace('Z', '+00:00'))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'video_id': self.video_id,
            'title': self.title,
            'channel_name': self.channel_name,
            'text': self.text,
            'transcript': self.text,  # Alias for compatibility
            'publish_date': self.publish_date,
            'published_at': self.publish_date,  # Alias for compatibility
            'duration': self.duration,
            'summary': self.summary,
            'enhanced_transcript': self.enhanced_transcript,
            'metadata': self.metadata,
            'url': self.url
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Transcript':
        """Create Transcript from dictionary."""
        # Handle various field name aliases
        text = data.get('text') or data.get('transcript') or data.get('content', '')
        publish_date = data.get('publish_date') or data.get('published_at', '')

        return cls(
            video_id=data['video_id'],
            title=data['title'],
            channel_name=data['channel_name'],
            text=text,
            publish_date=publish_date,
            duration=data.get('duration', 0),
            summary=data.get('summary'),
            enhanced_transcript=data.get('enhanced_transcript'),
            metadata=data.get('metadata')
        )
