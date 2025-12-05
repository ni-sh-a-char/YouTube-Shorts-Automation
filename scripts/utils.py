# FILE: scripts/utils.py
# Utility functions for YouTube Shorts automation

import os
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None


# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def setup_logging(
    name: str = 'shorts_automation',
    level: str = 'INFO',
    log_dir: Optional[Path] = None,
    file_output: bool = True,
    console_output: bool = True,
) -> logging.Logger:
    """
    Configure logging to console and file.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        file_output: Write logs to file
        console_output: Write logs to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Format
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_output and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f'shorts_automation_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# ============================================================================
# DIRECTORY UTILITIES
# ============================================================================

def ensure_directories(paths: List[Path]) -> None:
    """Ensure all directories exist."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def cleanup_directory(directory: Path, pattern: str = '*', keep_subdirs: bool = False) -> int:
    """
    Clean up files in a directory.
    
    Args:
        directory: Directory to clean
        pattern: File pattern to match (e.g., '*.wav', '*.mp4')
        keep_subdirs: Keep subdirectories
        
    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0
    
    count = 0
    for file_path in directory.glob(pattern):
        if keep_subdirs and file_path.is_dir():
            continue
        
        try:
            if file_path.is_file():
                file_path.unlink()
                count += 1
        except Exception as e:
            print(f"⚠️ Failed to delete {file_path}: {e}")
    
    return count


# ============================================================================
# METADATA UTILITIES
# ============================================================================

def save_metadata(
    metadata: Dict[str, Any],
    output_file: Path,
    video_id: Optional[str] = None,
) -> bool:
    """
    Save metadata to JSON file.
    
    Args:
        metadata: Metadata dictionary
        output_file: Output JSON file path
        video_id: YouTube video ID (optional, added to metadata)
        
    Returns:
        True if successful
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if video_id:
            metadata['youtube_video_id'] = video_id
        
        metadata['saved_at'] = datetime.now().isoformat()
        
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return True
    except Exception as e:
        print(f"❌ Failed to save metadata to {output_file}: {e}")
        return False


def log_metadata(metadata: Dict[str, Any], filename_prefix: str = 'metadata') -> Optional[Path]:
    """Save metadata with a timestamped filename into the output directory.

    Returns the Path to the saved file or None on failure.
    """
    try:
        output_dir = Path(os.getenv('OUTPUT_DIR', './data/output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = output_dir / f"{filename_prefix}_{timestamp}.json"
        success = save_metadata(metadata, out_file)
        return out_file if success else None
    except Exception as e:
        print(f"❌ Failed to log metadata: {e}")
        return None


def load_metadata(metadata_file: Path) -> Optional[Dict[str, Any]]:
    """
    Load metadata from JSON file.
    
    Args:
        metadata_file: Path to JSON metadata file
        
    Returns:
        Metadata dictionary or None if failed
    """
    try:
        with open(metadata_file) as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load metadata from {metadata_file}: {e}")
        return None


# ============================================================================
# VIDEO UTILITIES
# ============================================================================

def get_video_duration(video_path: Path) -> float:
    """
    Get video duration in seconds.
    
    Requires: moviepy or ffprobe
    """
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(str(video_path))
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        print(f"⚠️ Failed to get video duration for {video_path}: {e}")
        return 0.0


def get_audio_duration(audio_path: Path) -> float:
    """
    Get audio duration in seconds.
    
    Requires: moviepy or ffprobe
    """
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(str(audio_path))
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        print(f"⚠️ Failed to get audio duration for {audio_path}: {e}")
        return 0.0


# ============================================================================
# TEXT UTILITIES
# ============================================================================

def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_title_for_shorts(title: str, max_length: int = 100, auto_tag: bool = True) -> str:
    """
    Format title for YouTube Shorts.
    
    Args:
        title: Original title
        max_length: Maximum title length
        auto_tag: Add #Shorts tag
        
    Returns:
        Formatted title
    """
    # Truncate if necessary
    formatted = truncate_text(title.strip(), max_length - 8 if auto_tag else max_length)
    
    # Add Shorts tag
    if auto_tag and '#Shorts' not in formatted:
        formatted = f"{formatted} #Shorts"
    
    return formatted


def extract_keywords(text: str, min_keywords: int = 3, max_keywords: int = 7) -> List[str]:
    """
    Extract keywords from text (simple implementation).
    
    Args:
        text: Input text
        min_keywords: Minimum keywords to extract
        max_keywords: Maximum keywords to extract
        
    Returns:
        List of keywords
    """
    # Simple keyword extraction: words longer than 4 chars, excluding common words
    common_words = {
        'the', 'and', 'with', 'from', 'into', 'that', 'this', 'code',
        'using', 'about', 'will', 'have', 'make', 'your', 'which'
    }
    
    words = text.lower().split()
    keywords = [
        w.strip('.,!?;:')
        for w in words
        if len(w) > 4 and w.lower() not in common_words
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            unique_keywords.append(kw)
            seen.add(kw)
    
    return unique_keywords[min_keywords:max_keywords]


def format_description(
    script: str,
    hashtags: str = '',
    topic: str = '',
    channel_url: str = '',
) -> str:
    """
    Format video description for YouTube.
    
    Args:
        script: Video script or summary
        hashtags: Space-separated hashtags
        topic: Topic/category
        channel_url: Channel URL (optional)
        
    Returns:
        Formatted description
    """
    description_parts = [script]
    
    if channel_url:
        description_parts.append(f"\n🔗 More tutorials: {channel_url}")
    
    if topic:
        description_parts.append(f"\n📚 Topic: {topic}")
    
    if hashtags:
        description_parts.append(f"\n{hashtags}")
    
    return '\n'.join(description_parts)


# ============================================================================
# IMAGE UTILITIES
# ============================================================================

def fetch_image_from_pexels(
    query: str,
    api_key: str,
    orientation: str = 'portrait',
) -> Optional[Image.Image]:
    """
    Fetch image from Pexels API.
    
    Args:
        query: Search query
        api_key: Pexels API key
        orientation: 'portrait' or 'landscape'
        
    Returns:
        PIL Image or None if failed
    """
    if Image is None:
        print("⚠️ PIL not available for image processing")
        return None
    
    try:
        headers = {"Authorization": api_key}
        params = {
            "query": query,
            "per_page": 1,
            "orientation": orientation
        }
        
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        
        data = response.json()
        if data.get('photos'):
            image_url = data['photos'][0]['src']['large2x']
            image_response = requests.get(image_url, timeout=15)
            image_response.raise_for_status()
            return Image.open(BytesIO(image_response.content)).convert("RGBA")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching image from Pexels: {e}")
    except Exception as e:
        print(f"❌ Error fetching image from Pexels: {e}")
    
    return None


def create_solid_color_image(
    width: int,
    height: int,
    color: tuple = (12, 17, 29),
) -> Optional[Image.Image]:
    """
    Create solid color image.
    
    Args:
        width: Image width
        height: Image height
        color: RGB color tuple
        
    Returns:
        PIL Image
    """
    if Image is None:
        return None
    
    return Image.new('RGB', (width, height), color)


# ============================================================================
# FILE UTILITIES
# ============================================================================

def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    if not file_path.exists():
        return 0.0
    return file_path.stat().st_size / (1024 * 1024)


def format_file_size(size_bytes: int) -> str:
    """Format file size for display."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def is_valid_youtube_video_id(video_id: str) -> bool:
    """Validate YouTube video ID format."""
    return len(video_id) == 11 and all(c.isalnum() or c in '_-' for c in video_id)


def is_valid_resolution(width: int, height: int) -> bool:
    """Validate video resolution."""
    # Shorts: 1080x1920 (vertical)
    # Long-form: 1920x1080 (horizontal)
    vertical = (width == 1080 and height == 1920)
    horizontal = (width == 1920 and height == 1080)
    return vertical or horizontal


# ============================================================================
# TIME UTILITIES
# ============================================================================

def get_timestamp_str() -> str:
    """Get current timestamp as formatted string."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def iso_to_human_readable(iso_string: str) -> str:
    """Convert ISO timestamp to human-readable format."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return iso_string
