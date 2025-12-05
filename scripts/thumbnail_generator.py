# FILE: scripts/thumbnail_generator.py
# Thumbnail generation for YouTube Shorts

from pathlib import Path
from typing import Optional
from src.generator import generate_visuals
from scripts.config import get_config


class ThumbnailGenerator:
    """Generate thumbnails for YouTube Shorts."""
    
    def __init__(self):
        self.config = get_config()
    
    def generate_thumbnail(
        self,
        title: str,
        output_dir: Path,
    ) -> Optional[Path]:
        """
        Generate YouTube Shorts thumbnail.
        
        Args:
            title: Video title/theme
            output_dir: Output directory
            
        Returns:
            Path to thumbnail image
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Use existing generate_visuals function (optimized for vertical format)
            thumbnail_path = generate_visuals(
                output_dir=output_dir,
                video_type='short',
                thumbnail_title=title
            )
            
            print(f"✅ Thumbnail generated: {thumbnail_path}")
            return Path(thumbnail_path)
        
        except Exception as e:
            print(f"❌ Failed to generate thumbnail: {e}")
            return None


def generate_shorts_thumbnail(
    title: str,
    output_dir: Path,
) -> Optional[Path]:
    """
    Convenience function to generate Shorts thumbnail.
    
    Args:
        title: Video title
        output_dir: Output directory
        
    Returns:
        Path to thumbnail image
    """
    generator = ThumbnailGenerator()
    return generator.generate_thumbnail(title, output_dir)


if __name__ == '__main__':
    print("✅ Thumbnail generator module loaded")
