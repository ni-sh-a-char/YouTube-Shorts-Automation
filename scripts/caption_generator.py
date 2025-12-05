# FILE: scripts/caption_generator.py
# Auto-generate captions and subtitle overlays for YouTube Shorts

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


@dataclass
class Caption:
    """Caption with timing information."""
    start_time: float  # seconds
    end_time: float
    text: str
    
    def to_srt(self, index: int) -> str:
        """Convert to SRT format."""
        def seconds_to_srt_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
        return f"{index}\n{seconds_to_srt_time(self.start_time)} --> {seconds_to_srt_time(self.end_time)}\n{self.text}\n"


class CaptionGenerator:
    """Generate captions and subtitle overlays."""
    
    def __init__(self, duration_seconds: int = 15):
        self.duration_seconds = duration_seconds
    
    def generate_from_visual_cues(
        self,
        visual_cues: List[Dict],
        script: str,
    ) -> List[Caption]:
        """
        Generate captions from visual cues and script.
        
        Args:
            visual_cues: List of visual cues with timing
            script: Script text
            
        Returns:
            List of Caption objects
        """
        captions = []
        
        # Extract sentences from script and match with visual cues
        sentences = [s.strip() for s in script.split('.') if s.strip()]
        
        for i, cue in enumerate(visual_cues):
            start_time = cue.get('time_seconds', 0)
            end_time = visual_cues[i + 1].get('time_seconds', self.duration_seconds) if i + 1 < len(visual_cues) else self.duration_seconds
            
            # Use corresponding sentence as caption
            caption_text = sentences[i] if i < len(sentences) else cue.get('cue', '')
            
            captions.append(Caption(start_time, end_time, caption_text))
        
        return captions
    
    def save_srt(
        self,
        captions: List[Caption],
        output_path: Path,
    ) -> bool:
        """
        Save captions as SRT file.
        
        Args:
            captions: List of captions
            output_path: Output SRT file path
            
        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            srt_content = ''
            for i, caption in enumerate(captions, 1):
                srt_content += caption.to_srt(i) + '\n'
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            print(f"✅ Captions saved: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to save SRT captions: {e}")
            return False
    
    def generate_caption_frames(
        self,
        captions: List[Caption],
        video_resolution: Tuple[int, int] = (1080, 1920),
        font_size: int = 40,
        font_color: str = '#FFFFFF',
        bg_color: str = '#000000',
        bg_alpha: float = 0.5,
    ) -> Dict[str, Path]:
        """
        Generate image frames with captions embedded.
        
        Args:
            captions: List of captions
            video_resolution: (width, height)
            font_size: Font size
            font_color: Text color (hex)
            bg_color: Background color (hex)
            bg_alpha: Background alpha (0.0-1.0)
            
        Returns:
            Dictionary mapping time offsets to image paths
        """
        if Image is None:
            print("⚠️ PIL not available for caption embedding")
            return {}
        
        frames = {}
        width, height = video_resolution
        
        for caption in captions:
            # Create transparent image
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Load font
            try:
                font = ImageFont.truetype('arial.ttf', font_size)
            except:
                font = ImageFont.load_default()
            
            # Convert hex colors to RGB tuples
            font_rgb = tuple(int(font_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            bg_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            # Calculate text position and size
            bbox = draw.textbbox((0, 0), caption.text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = height - text_height - 40  # Bottom of video
            
            # Draw background box
            padding = 10
            draw.rectangle(
                [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
                fill=(*bg_rgb, int(255 * bg_alpha))
            )
            
            # Draw text
            draw.text((x, y), caption.text, font=font, fill=(*font_rgb, 255))
            
            # Save frame
            frame_path = Path(f'caption_frame_{int(caption.start_time*10)}.png')
            img.save(frame_path)
            frames[str(caption.start_time)] = frame_path
        
        return frames


def generate_captions(
    script: str,
    visual_cues: List[Dict],
    output_srt: Path,
    duration_seconds: int = 15,
) -> bool:
    """
    Convenience function to generate and save captions.
    
    Args:
        script: Script text
        visual_cues: Visual cues with timing
        output_srt: Output SRT file path
        duration_seconds: Video duration
        
    Returns:
        True if successful
    """
    generator = CaptionGenerator(duration_seconds)
    captions = generator.generate_from_visual_cues(visual_cues, script)
    return generator.save_srt(captions, output_srt)


if __name__ == '__main__':
    print("✅ Caption generator module loaded")
