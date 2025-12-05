# FILE: scripts/video_editor.py
# Video composition for YouTube Shorts (uses existing generator.py functions)

from pathlib import Path
from typing import List, Optional, Tuple
from src.generator import create_video
from scripts.config import get_config


class VideoEditor:
    """Video editing for YouTube Shorts."""
    
    def __init__(self):
        self.config = get_config()
    
    def create_short_video(
        self,
        slide_paths: List[str],
        audio_paths: List[str],
        output_path: Path,
        captions_srt: Optional[Path] = None,
    ) -> bool:
        """
        Create vertical YouTube Shorts video.
        
        Args:
            slide_paths: List of slide image paths
            audio_paths: List of audio file paths
            output_path: Output video file path
            captions_srt: Optional SRT captions file
            
        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use existing create_video function from generator.py
            create_video(slide_paths, audio_paths, output_path, 'short')
            
            # TODO: Add caption embedding if captions_srt provided
            # This would require ffmpeg-python for SRT overlay
            
            if captions_srt and captions_srt.exists():
                print(f"💡 Caption file available at: {captions_srt}")
                print(f"   Use FFmpeg to embed: ffmpeg -i {output_path} -vf subtitles={captions_srt} {output_path}.with_subs.mp4")
            
            return True
        except Exception as e:
            print(f"❌ Failed to create video: {e}")
            return False

    def create_shorts_video(
        self,
        script_data: dict,
        captions_srt_path: str | None,
        thumbnail_path: str,
        title: str | None,
        output_file: str,
        timestamp: str | None = None,
    ) -> str:
        """Compatibility wrapper used by the scheduler.

        Accepts single-audio + thumbnail inputs and produces a Shorts video.
        Internally converts these into the slide/audio lists expected by
        `create_short_video` and returns the output file path string on
        success, otherwise raises an exception.
        """
        output_path = Path(output_file)
        try:
            # Prepare working dirs
            ts = timestamp or ''
            out_dir = output_path.parent
            slides_dir = out_dir / f"slides_{ts}"
            audio_dir = out_dir / f"audio_{ts}"
            slides_dir.mkdir(parents=True, exist_ok=True)
            audio_dir.mkdir(parents=True, exist_ok=True)

            # Use visual cues from script_data if available, otherwise split script into sentences
            visual_cues = script_data.get('visual_cues') or []
            script_text = script_data.get('script', '')

            # Generate a single audio file for the entire script
            # (no per-segment generation to avoid duplication)
            from src.tts_generator import generate_voice
            from src.generator import generate_visuals

            # Generate the complete audio once
            audio_dir.mkdir(parents=True, exist_ok=True)
            full_audio_path = audio_dir / f"audio_full_{ts}.mp3"
            
            # Use edge-tts to generate one continuous audio file
            try:
                generate_voice(script_text, str(full_audio_path))
            except Exception as e:
                print(f"⚠️ edge-tts failed ({e}), trying fallback gTTS...")
                from gtts import gTTS
                tts = gTTS(text=script_text, lang='en', slow=False)
                tts.save(str(full_audio_path))
            
            # If visual_cues are not provided, generate them from the script
            if not visual_cues:
                # Split script into chunks for visual cues (ignoring [PAUSE] for now)
                chunks = [s.strip() for s in script_text.replace('[PAUSE]', '.').split('.') if s.strip()]
                seg_len = max(1, int(script_data.get('duration_seconds', self.config.video_duration_seconds) / max(1, len(chunks))))
                visual_cues = [{'time_seconds': i * seg_len, 'type': 'text', 'content': chunk[:120]} for i, chunk in enumerate(chunks)]

            # Generate slides only (use the single audio file)
            slide_paths = []

            for i, cue in enumerate(visual_cues):
                # Get content from either 'cue' (legacy) or 'content' (new format)
                cue_text = cue.get('content') or cue.get('cue', '')
                slide_path = generate_visuals(output_dir=slides_dir, video_type='short', slide_content={'title': title or '', 'content': cue_text}, slide_number=i+1, total_slides=len(visual_cues))
                slide_paths.append(str(slide_path))

            success = self.create_short_video(
                slide_paths=slide_paths,
                audio_paths=[str(full_audio_path)],
                output_path=output_path,
                captions_srt=Path(captions_srt_path) if captions_srt_path else None,
            )

            if not success:
                raise RuntimeError("VideoEditor failed to create the short video")

            return str(output_path)

        except Exception as e:
            print(f"❌ create_shorts_video failed: {e}")
            raise


def create_shorts_video(
    slide_paths: List[str],
    audio_paths: List[str],
    output_path: Path,
) -> bool:
    """
    Convenience function to create Shorts video.
    
    Args:
        slide_paths: List of slides
        audio_paths: List of audio clips
        output_path: Output path
        
    Returns:
        True if successful
    """
    editor = VideoEditor()
    return editor.create_short_video(slide_paths, audio_paths, output_path)


if __name__ == '__main__':
    print("✅ Video editor module loaded")
