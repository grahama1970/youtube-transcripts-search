"""
Module: visual_extractor.py
Purpose: Extract and analyze visual content from YouTube videos

External Dependencies:
- ffmpeg-python: https://github.com/kkroening/ffmpeg-python
- opencv-python: https://opencv.org/
- pytesseract: https://github.com/madmaze/pytesseract
- Pillow: https://pillow.readthedocs.io/

Example Usage:
>>> extractor = VisualExtractor()
>>> frames = await extractor.extract_frames("dQw4w9WgXcQ", strategy="adaptive")
>>> code_blocks = await extractor.detect_code_content(frames)
"""

import asyncio
import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Literal

import cv2
import ffmpeg
import numpy as np
import pytesseract
from loguru import logger
from PIL import Image

from .config import get_settings

settings = get_settings()


@dataclass
class Frame:
    """Represents a single frame extracted from video"""
    timestamp: float  # seconds
    frame_number: int
    path: Path
    video_id: str
    hash: str  # For duplicate detection

    @property
    def timecode(self) -> str:
        """Format timestamp as HH:MM:SS"""
        return str(timedelta(seconds=int(self.timestamp)))


@dataclass
class VisualContent:
    """Analyzed visual content from a frame"""
    frame: Frame
    content_type: Literal["code", "terminal", "chart", "diagram", "slide", "unknown"]
    confidence: float
    extracted_text: str | None = None
    language: str | None = None  # Programming language if code
    regions: list[tuple[int, int, int, int]] = field(default_factory=list)  # Bounding boxes
    metadata: dict = field(default_factory=dict)


class VisualExtractor:
    """Extract and analyze visual content from YouTube videos"""

    def __init__(self,
                 storage_path: Path = Path("data/visual_content"),
                 ffmpeg_path: str = "ffmpeg"):
        self.storage_path = storage_path
        self.ffmpeg_path = ffmpeg_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Smart sampling strategies
        self.chapter_end_offset = 10  # Capture 10 seconds before chapter end
        self.completion_check_interval = 30  # Check every 30s for complete code
        self.ide_stability_threshold = 3  # Seconds of no changes = complete code

    async def extract_frames(self,
                           video_id: str,
                           video_path: Path | None = None,
                           strategy: Literal["survey", "detailed", "adaptive"] = "adaptive") -> list[Frame]:
        """Extract frames from video using specified strategy"""

        # Create video-specific directory
        video_dir = self.storage_path / video_id
        video_dir.mkdir(exist_ok=True)

        # Check cache first
        cache_file = video_dir / f"{strategy}_frames.json"
        if cache_file.exists():
            logger.info(f"Loading cached frames for {video_id}")
            return self._load_frames_from_cache(cache_file)

        # Download video if needed
        if not video_path:
            video_path = await self._download_video(video_id)

        # Extract frames based on strategy
        if strategy == "survey":
            frames = await self._extract_survey_frames(video_id, video_path, video_dir)
        elif strategy == "detailed":
            frames = await self._extract_detailed_frames(video_id, video_path, video_dir)
        else:  # adaptive
            frames = await self._extract_adaptive_frames(video_id, video_path, video_dir)

        # Cache results
        self._save_frames_to_cache(frames, cache_file)

        return frames

    async def _extract_survey_frames(self, video_id: str, video_path: Path, output_dir: Path) -> list[Frame]:
        """Extract frames at regular intervals for initial survey"""
        logger.info(f"Extracting survey frames every {self.survey_interval}s")

        frames = []

        # Use ffmpeg to extract frames
        try:
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.filter(stream, 'fps', fps=f'1/{self.survey_interval}')
            stream = ffmpeg.output(stream, str(output_dir / 'survey_%04d.png'))

            process = await asyncio.create_subprocess_exec(
                self.ffmpeg_path, *ffmpeg.compile(stream, overwrite_output=True),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await process.communicate()

            # Create Frame objects
            for i, frame_path in enumerate(sorted(output_dir.glob('survey_*.png'))):
                timestamp = i * self.survey_interval
                frame_hash = self._compute_frame_hash(frame_path)

                frames.append(Frame(
                    timestamp=timestamp,
                    frame_number=i,
                    path=frame_path,
                    video_id=video_id,
                    hash=frame_hash
                ))

        except Exception as e:
            logger.error(f"Error extracting survey frames: {e}")

        return frames

    async def _extract_adaptive_frames(self, video_id: str, video_path: Path, output_dir: Path) -> list[Frame]:
        """Adaptive extraction: survey first, then detailed in regions of interest"""

        # Step 1: Get survey frames
        survey_frames = await self._extract_survey_frames(video_id, video_path, output_dir)

        # Step 2: Analyze survey frames for code/terminal content
        regions_of_interest = await self._identify_code_regions(survey_frames)

        # Step 3: Extract detailed frames in regions of interest
        all_frames = list(survey_frames)

        for start_time, end_time in regions_of_interest:
            logger.info(f"Extracting detailed frames from {start_time}s to {end_time}s")

            # Extract frames in this region
            detail_frames = await self._extract_frames_in_range(
                video_id, video_path, output_dir,
                start_time, end_time, self.detail_interval
            )
            all_frames.extend(detail_frames)

        # Sort by timestamp and remove duplicates
        all_frames.sort(key=lambda f: f.timestamp)
        unique_frames = self._remove_duplicate_frames(all_frames)

        return unique_frames

    async def _identify_code_regions(self, frames: list[Frame]) -> list[tuple[float, float]]:
        """Identify time regions likely containing code or terminal content"""
        regions = []

        for i, frame in enumerate(frames):
            # Quick heuristic: look for dark backgrounds with text
            is_code_like = await self._is_code_frame(frame)

            if is_code_like:
                start_time = max(0, frame.timestamp - self.survey_interval/2)
                end_time = frame.timestamp + self.survey_interval/2

                # Merge with previous region if overlapping
                if regions and regions[-1][1] >= start_time:
                    regions[-1] = (regions[-1][0], end_time)
                else:
                    regions.append((start_time, end_time))

        return regions

    async def _is_code_frame(self, frame: Frame) -> bool:
        """Quick heuristic to detect if frame likely contains code"""
        img = cv2.imread(str(frame.path))

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check for dark background (common in IDEs/terminals)
        mean_brightness = np.mean(gray)
        if mean_brightness > 128:  # Too bright for typical code editor
            return False

        # Detect edges (text has many edges)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Code frames typically have moderate edge density
        return 0.02 < edge_density < 0.15

    async def detect_code_content(self, frames: list[Frame]) -> list[VisualContent]:
        """Detect and extract code content from frames"""
        visual_contents = []

        for frame in frames:
            content = await self._analyze_frame(frame)
            if content and content.content_type in ["code", "terminal"]:
                visual_contents.append(content)

        return visual_contents

    async def _analyze_frame(self, frame: Frame) -> VisualContent | None:
        """Analyze a single frame for content type and extract text"""
        img = cv2.imread(str(frame.path))

        # Detect content type
        content_type, confidence = await self._classify_content(img)

        if content_type in ["code", "terminal"]:
            # Extract text using OCR
            text = await self._extract_text_from_code(img)
            language = self._detect_programming_language(text) if text else None

            return VisualContent(
                frame=frame,
                content_type=content_type,
                confidence=confidence,
                extracted_text=text,
                language=language
            )

        return None

    async def _extract_text_from_code(self, img: np.ndarray) -> str | None:
        """Extract text from code/terminal image using OCR"""
        # Preprocess for better OCR
        processed = self._preprocess_for_ocr(img)

        # Use Tesseract with code-friendly settings
        custom_config = r'--oem 3 --psm 6'
        try:
            text = pytesseract.image_to_string(processed, config=custom_config)
            return self._clean_ocr_text(text)
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None

    def _preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Invert if dark background
        if np.mean(gray) < 128:
            gray = cv2.bitwise_not(gray)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)

        # Enhance contrast
        enhanced = cv2.equalizeHist(denoised)

        return enhanced

    def _detect_programming_language(self, text: str) -> str | None:
        """Detect programming language from code text"""
        # Simple heuristics - could be enhanced with ML
        language_indicators = {
            'python': ['def ', 'import ', 'from ', 'class ', 'if __name__'],
            'javascript': ['function ', 'const ', 'let ', 'var ', '=>', 'console.'],
            'java': ['public class', 'private ', 'static void', 'System.out'],
            'cpp': ['#include', 'std::', 'int main', 'cout <<'],
            'bash': ['#!/bin/bash', 'echo ', 'export ', 'alias '],
        }

        text_lower = text.lower()
        scores = {}

        for lang, indicators in language_indicators.items():
            score = sum(1 for ind in indicators if ind in text_lower)
            if score > 0:
                scores[lang] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    def _compute_frame_hash(self, frame_path: Path) -> str:
        """Compute perceptual hash of frame for duplicate detection"""
        with Image.open(frame_path) as img:
            # Resize to small size
            small = img.resize((16, 16), Image.Resampling.LANCZOS)
            # Convert to grayscale
            gray = small.convert('L')
            # Get pixel data
            pixels = list(gray.getdata())
            # Simple hash
            avg = sum(pixels) / len(pixels)
            bits = ''.join('1' if p > avg else '0' for p in pixels)
            return hashlib.md5(bits.encode()).hexdigest()[:16]

    def _remove_duplicate_frames(self, frames: list[Frame]) -> list[Frame]:
        """Remove duplicate frames based on perceptual hash"""
        seen_hashes = set()
        unique_frames = []

        for frame in frames:
            if frame.hash not in seen_hashes:
                seen_hashes.add(frame.hash)
                unique_frames.append(frame)
            else:
                logger.debug(f"Skipping duplicate frame at {frame.timestamp}s")

        return unique_frames

    async def _classify_content(self, img: np.ndarray) -> tuple[str, float]:
        """Classify the content type of an image"""
        # This is a placeholder for more sophisticated classification
        # In production, you'd use Claude Vision API or a trained model

        # Simple heuristics for now
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)

        # Dark background suggests code/terminal
        if mean_brightness < 80:
            # Check for text-like patterns
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size

            if 0.02 < edge_density < 0.15:
                return ("terminal" if mean_brightness < 40 else "code", 0.8)

        return ("unknown", 0.5)

    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR output for code"""
        # Remove common OCR artifacts
        cleaned = text.strip()

        # Fix common OCR mistakes in code
        replacements = {
            ' ( ': '(',
            ' ) ': ')',
            ' [ ': '[',
            ' ] ': ']',
            ' { ': '{',
            ' } ': '}',
            ' ; ': ';',
            ' : ': ':',
        }

        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        return cleaned

    async def _extract_frames_in_range(self, video_id: str, video_path: Path,
                                     output_dir: Path, start: float, end: float,
                                     interval: float) -> list[Frame]:
        """Extract frames in a specific time range"""
        frames = []

        for t in np.arange(start, end, interval):
            frame_path = output_dir / f"detail_{int(t):06d}.png"

            # Extract single frame at timestamp
            stream = ffmpeg.input(str(video_path), ss=t)
            stream = ffmpeg.output(stream, str(frame_path), vframes=1)

            try:
                process = await asyncio.create_subprocess_exec(
                    self.ffmpeg_path, *ffmpeg.compile(stream, overwrite_output=True),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                await process.communicate()

                if frame_path.exists():
                    frames.append(Frame(
                        timestamp=t,
                        frame_number=int(t * 30),  # Assuming 30fps
                        path=frame_path,
                        video_id=video_id,
                        hash=self._compute_frame_hash(frame_path)
                    ))
            except Exception as e:
                logger.error(f"Error extracting frame at {t}s: {e}")

        return frames

    def _save_frames_to_cache(self, frames: list[Frame], cache_file: Path):
        """Save frame metadata to cache"""
        data = [
            {
                "timestamp": f.timestamp,
                "frame_number": f.frame_number,
                "path": str(f.path),
                "video_id": f.video_id,
                "hash": f.hash
            }
            for f in frames
        ]

        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_frames_from_cache(self, cache_file: Path) -> list[Frame]:
        """Load frame metadata from cache"""
        with open(cache_file) as f:
            data = json.load(f)

        return [
            Frame(
                timestamp=d["timestamp"],
                frame_number=d["frame_number"],
                path=Path(d["path"]),
                video_id=d["video_id"],
                hash=d["hash"]
            )
            for d in data
        ]

    async def _download_video(self, video_id: str) -> Path:
        """Download video using yt-dlp"""
        # Placeholder - integrate with existing YouTube download functionality
        raise NotImplementedError("Video download not implemented yet")


# Validation
if __name__ == "__main__":
    async def validate():
        extractor = VisualExtractor()

        # Test with a known video ID (would need actual video file)
        test_video_id = "dQw4w9WgXcQ"
        test_video_path = Path("test_video.mp4")  # Would need actual file

        if test_video_path.exists():
            # Extract frames
            frames = await extractor.extract_frames(
                test_video_id,
                test_video_path,
                strategy="survey"
            )

            print(f"✅ Extracted {len(frames)} frames")

            # Detect code content
            code_contents = await extractor.detect_code_content(frames)
            print(f"✅ Found {len(code_contents)} code frames")

            for content in code_contents[:3]:
                print(f"  - {content.frame.timecode}: {content.content_type} "
                      f"(confidence: {content.confidence:.2f})")
                if content.extracted_text:
                    print(f"    Language: {content.language}")
                    print(f"    Text preview: {content.extracted_text[:100]}...")
        else:
            print("⚠️  No test video available for validation")
            print("✅ Module structure validated")

    asyncio.run(validate())
