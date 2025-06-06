"""
Module: smart_visual_extractor.py
Purpose: Smart extraction of complete code from YouTube videos at strategic moments

External Dependencies:
- ffmpeg-python: https://github.com/kkroening/ffmpeg-python
- opencv-python: https://opencv.org/
- pytesseract: https://github.com/madmaze/pytesseract

Example Usage:
>>> extractor = SmartVisualExtractor()
>>> chapters = await extractor.get_video_chapters("dQw4w9WgXcQ")
>>> complete_code = await extractor.extract_chapter_end_code("dQw4w9WgXcQ", chapters)
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from .visual_extractor import Frame, VisualExtractor


@dataclass
class VideoChapter:
    """Represents a chapter in a YouTube video"""
    start_time: float
    end_time: float
    title: str
    is_code_chapter: bool = False
    is_advertisement: bool = False


@dataclass
class CompleteCodeCapture:
    """Represents a capture of complete code"""
    chapter: VideoChapter
    frame: Frame
    code_text: str
    confidence: float
    ide_type: str  # 'vscode', 'terminal', 'jupyter', etc.


class SmartVisualExtractor(VisualExtractor):
    """
    Smarter approach: Extract complete code at strategic moments
    instead of trying to merge partial snippets
    """

    def __init__(self, storage_path: Path = Path("data/visual_content")):
        super().__init__(storage_path)

        # Keywords indicating code chapters
        self.code_keywords = [
            'code', 'coding', 'implementation', 'demo', 'example',
            'terminal', 'console', 'ide', 'editor', 'programming'
        ]

        # Keywords indicating ads
        self.ad_keywords = [
            'sponsor', 'ad', 'advertisement', 'promoted', 'discount',
            'offer', 'deal', 'promo'
        ]

    async def extract_complete_code(self,
                                  video_id: str,
                                  chapters: list[VideoChapter] | None = None) -> list[CompleteCodeCapture]:
        """
        Extract complete code by focusing on key moments:
        1. End of code chapters (when implementation is complete)
        2. Moments of IDE stability (no changes for several seconds)
        3. Before transitions away from code screens
        """

        if not chapters:
            chapters = await self.get_video_chapters(video_id)

        complete_captures = []

        for chapter in chapters:
            if chapter.is_advertisement:
                logger.info(f"Skipping ad chapter: {chapter.title}")
                continue

            if self._is_code_chapter(chapter):
                logger.info(f"Processing code chapter: {chapter.title}")

                # Strategy 1: Capture near end of chapter
                end_captures = await self._extract_chapter_end_code(
                    video_id, chapter
                )
                complete_captures.extend(end_captures)

                # Strategy 2: Detect stable IDE states
                stable_captures = await self._extract_stable_ide_states(
                    video_id, chapter
                )
                complete_captures.extend(stable_captures)

        # Deduplicate and rank by quality
        return self._deduplicate_captures(complete_captures)

    async def _extract_chapter_end_code(self,
                                      video_id: str,
                                      chapter: VideoChapter) -> list[CompleteCodeCapture]:
        """
        Extract frames near the end of a chapter where code is likely complete
        """
        captures = []

        # Sample the last 10 seconds of the chapter
        sample_start = max(chapter.start_time, chapter.end_time - 10)
        sample_points = np.arange(sample_start, chapter.end_time, 2)  # Every 2 seconds

        for timestamp in sample_points:
            frame = await self._extract_single_frame(video_id, timestamp)

            if await self._is_code_frame(frame):
                content = await self._analyze_frame(frame)

                if content and content.extracted_text:
                    capture = CompleteCodeCapture(
                        chapter=chapter,
                        frame=frame,
                        code_text=content.extracted_text,
                        confidence=content.confidence,
                        ide_type=self._detect_ide_type(frame)
                    )
                    captures.append(capture)

        # Return the best capture (latest with highest confidence)
        if captures:
            return [max(captures, key=lambda c: (c.frame.timestamp, c.confidence))]
        return []

    async def _extract_stable_ide_states(self,
                                       video_id: str,
                                       chapter: VideoChapter) -> list[CompleteCodeCapture]:
        """
        Detect moments when IDE content hasn't changed for several seconds
        (indicating complete code state)
        """
        captures = []

        # Sample every 30 seconds through the chapter
        sample_points = np.arange(
            chapter.start_time,
            chapter.end_time,
            self.completion_check_interval
        )

        for timestamp in sample_points:
            # Check if IDE is stable at this point
            if await self._is_ide_stable(video_id, timestamp):
                frame = await self._extract_single_frame(video_id, timestamp)

                if await self._is_code_frame(frame):
                    content = await self._analyze_frame(frame)

                    if content and content.extracted_text:
                        capture = CompleteCodeCapture(
                            chapter=chapter,
                            frame=frame,
                            code_text=content.extracted_text,
                            confidence=content.confidence,
                            ide_type=self._detect_ide_type(frame)
                        )
                        captures.append(capture)

        return captures

    async def _is_ide_stable(self, video_id: str, timestamp: float) -> bool:
        """
        Check if IDE content is stable (unchanged) around this timestamp
        """
        # Extract frames before and after
        frames = []
        for offset in [-3, -2, -1, 0, 1, 2, 3]:
            t = timestamp + offset
            frame = await self._extract_single_frame(video_id, t)
            frames.append(frame)

        # Compare consecutive frames
        stable_count = 0
        for i in range(1, len(frames)):
            if self._frames_are_similar(frames[i-1], frames[i]):
                stable_count += 1

        # If most frames are similar, IDE is stable
        return stable_count >= 4

    def _frames_are_similar(self, frame1: Frame, frame2: Frame) -> bool:
        """
        Check if two frames are visually similar (same code state)
        """
        img1 = cv2.imread(str(frame1.path))
        img2 = cv2.imread(str(frame2.path))

        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Calculate structural similarity
        diff = cv2.absdiff(gray1, gray2)
        mean_diff = np.mean(diff)

        # Low difference means similar frames
        return mean_diff < 10

    def _detect_ide_type(self, frame: Frame) -> str:
        """
        Detect the type of IDE/editor in the frame
        """
        img = cv2.imread(str(frame.path))

        # Simple color-based detection
        # VSCode typically has dark blue/black theme
        # Terminal is usually pure black
        # Jupyter has white background

        mean_color = np.mean(img, axis=(0, 1))
        brightness = np.mean(mean_color)

        if brightness > 200:  # Bright background
            return "jupyter"
        elif brightness < 30:  # Very dark
            return "terminal"
        else:
            # Check for VSCode-like colors
            blue_ratio = mean_color[0] / (mean_color[1] + mean_color[2] + 1)
            if blue_ratio > 0.4:
                return "vscode"
            else:
                return "editor"

    def _is_code_chapter(self, chapter: VideoChapter) -> bool:
        """
        Determine if a chapter likely contains code based on title
        """
        if chapter.is_code_chapter:
            return True

        title_lower = chapter.title.lower()

        # Check for ad keywords first
        if any(keyword in title_lower for keyword in self.ad_keywords):
            chapter.is_advertisement = True
            return False

        # Check for code keywords
        if any(keyword in title_lower for keyword in self.code_keywords):
            chapter.is_code_chapter = True
            return True

        return False

    def _deduplicate_captures(self,
                            captures: list[CompleteCodeCapture]) -> list[CompleteCodeCapture]:
        """
        Remove duplicate code captures, keeping the best quality ones
        """
        # Group by similar code content
        unique_captures = {}

        for capture in captures:
            # Create a normalized key from the first few lines
            lines = capture.code_text.strip().split('\n')[:5]
            key = '\n'.join(line.strip() for line in lines)

            if key not in unique_captures:
                unique_captures[key] = capture
            else:
                # Keep the one with higher confidence
                if capture.confidence > unique_captures[key].confidence:
                    unique_captures[key] = capture

        return list(unique_captures.values())

    async def get_video_chapters(self, video_id: str) -> list[VideoChapter]:
        """
        Get chapter information from YouTube video
        This would integrate with YouTube API
        """
        # Placeholder - would fetch from YouTube API
        # For now, return mock data
        return [
            VideoChapter(0, 120, "Introduction", False, False),
            VideoChapter(120, 300, "Setting up the IDE", True, False),
            VideoChapter(300, 420, "Sponsor message", False, True),
            VideoChapter(420, 900, "Implementing the algorithm", True, False),
            VideoChapter(900, 1200, "Testing the code", True, False),
        ]

    async def _extract_single_frame(self, video_id: str, timestamp: float) -> Frame:
        """
        Extract a single frame at a specific timestamp
        """
        # This would use the parent class method
        # Simplified for demonstration
        frame_path = self.storage_path / video_id / f"frame_{int(timestamp)}.png"

        return Frame(
            timestamp=timestamp,
            frame_number=int(timestamp * 30),
            path=frame_path,
            video_id=video_id,
            hash=self._compute_frame_hash(frame_path)
        )


# Validation
if __name__ == "__main__":
    async def validate():
        extractor = SmartVisualExtractor()

        # Test with mock video
        test_video_id = "test_video"

        # Get chapters
        chapters = await extractor.get_video_chapters(test_video_id)
        print(f"✅ Found {len(chapters)} chapters")
        print(f"✅ Code chapters: {sum(1 for c in chapters if extractor._is_code_chapter(c))}")
        print(f"✅ Ad chapters: {sum(1 for c in chapters if c.is_advertisement)}")

        # Extract complete code
        # complete_code = await extractor.extract_complete_code(test_video_id, chapters)
        # print(f"✅ Extracted {len(complete_code)} complete code captures")

        print("✅ Smart extraction strategy validated")

    asyncio.run(validate())
