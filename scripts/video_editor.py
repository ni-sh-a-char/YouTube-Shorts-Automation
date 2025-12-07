# FILE: scripts/video_editor.py
# Video composition for YouTube Shorts (uses existing generator.py functions)

from pathlib import Path
from typing import List, Optional, Tuple
from src.generator import create_video
from scripts.config import get_config
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, TextClip, CompositeAudioClip, vfx
import math
import requests
import tempfile
from src.generator import get_pexels_video, get_pexels_image


def add_code_overlay(clip, code_text: str, duration: float = 2.0, position: Tuple[str, str] = ('center', 'bottom')):
    """
    Add code snippet as animated on-screen overlay.
    
    Args:
        clip: Video clip to add overlay to
        code_text: Code snippet to display
        duration: Duration to show code (seconds)
        position: Position tuple (x, y)
        
    Returns:
        CompositeVideoClip with code overlay
    """
    if not code_text or not code_text.strip():
        return clip
    
    try:
        from scripts.code_utils import format_code_for_display
        
        # Format code for display (max 3 lines)
        code_display = format_code_for_display(code_text, max_lines=3)
        
        # Create styled code clip
        code_clip = TextClip(
            code_display,
            fontsize=24,
            font='Courier New',
            color='#00FF00',  # Bright green
            method='caption',
            size=(clip.w - 60, None),
            stroke_color='#FF6B00',  # Orange outline
            stroke_width=2,
            bg_color='#0a0a0a',  # Nearly black
            align='center'
        ).set_duration(duration).set_position(position)
        
        return CompositeVideoClip([clip, code_clip])
    except Exception as e:
        import logging
        logging.warning(f"⚠️ Failed to add code overlay: {e}")
        return clip


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

            # Use visual cues from script_data if available, otherwise split script into chunks
            visual_cues = script_data.get('visual_cues') or []
            script_text = script_data.get('script', '')

            # TTS and visuals generator
            from src.tts_generator import generate_voice
            from src.generator import generate_visuals

            # Generate the complete audio (the TTS generator will split on [PAUSE]
            # and insert silences as required)
            full_audio_path = audio_dir / f"audio_full_{ts}.mp3"
            try:
                generate_voice(script_text, str(full_audio_path))
            except Exception as e:
                print(f"⚠️ TTS failed ({e}), trying fallback gTTS for full script...")
                from gtts import gTTS
                tts = gTTS(text=script_text.replace('[PAUSE]', ' '), lang='en', slow=False)
                tts.save(str(full_audio_path))

            # If visual_cues are not provided or missing timing, attempt to parse script_data
            if not visual_cues:
                chunks = [s.strip() for s in script_text.replace('[PAUSE]', '.').split('.') if s.strip()]
                dur = script_data.get('duration_seconds', self.config.video_duration_seconds)
                seg_len = max(1.0, dur / max(1, len(chunks)))
                visual_cues = [{'time_seconds': round(i * seg_len, 2), 'duration_seconds': round(seg_len, 2), 'type': 'text', 'content': chunk[:120]} for i, chunk in enumerate(chunks)]

            # Check if this is a coding topic and extract code snippets
            from scripts.code_utils import is_coding_topic, extract_code_markers
            is_coding = script_data.get('is_coding_topic', False) or is_coding_topic(script_data.get('topic', ''))
            code_snippets = []
            if is_coding:
                # Try to extract code from visual cues
                for cue in visual_cues:
                    cue_content = str(cue.get('content') or cue.get('cue', ''))
                    extracted = extract_code_markers([cue_content])
                    code_snippets.extend(extracted)

            # Generate image slides for each visual cue and prepare timed clips
            slide_items = []
            for i, cue in enumerate(visual_cues):
                cue_text = cue.get('content') or cue.get('cue', '')

                # For visual types that represent footage or images, try to fetch
                # matching stock video or image. If not available, fall back to
                # generated slide with the cue text.
                media_path = None
                media_is_video = False

                if cue.get('type') in ('b-roll', 'image', 'screenshot'):
                    # Try to fetch a relevant Pexels video first
                    try:
                        video_url = get_pexels_video(cue_text, orientation='portrait')
                        if video_url:
                            # Download to temp file
                            r = requests.get(video_url, stream=True, timeout=15)
                            if r.status_code == 200:
                                tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                with open(tmpf.name, 'wb') as fh:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        fh.write(chunk)
                                media_path = tmpf.name
                                media_is_video = True
                    except Exception:
                        media_path = None

                    # If no video found, try an image
                    if not media_path:
                        try:
                            img = get_pexels_image(cue_text, 'short')
                            if img:
                                tmpf = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                                img.save(tmpf.name)
                                media_path = tmpf.name
                                media_is_video = False
                        except Exception:
                            media_path = None

                # If media not found, fallback to generated slide with text
                if not media_path:
                    slide_path = generate_visuals(output_dir=slides_dir, video_type='short', slide_content={'title': title or '', 'content': cue_text}, slide_number=i+1, total_slides=len(visual_cues))
                    slide_items.append({'path': str(slide_path), 'cue': cue, 'is_video': False})
                else:
                    slide_items.append({'path': str(media_path), 'cue': cue, 'is_video': media_is_video})

            # Compose video using absolute cue timings so clips don't stack on top
            clips = []
            W, H = self.config.video_resolution
            for item in slide_items:
                path = item['path']
                cue = item['cue']
                is_video = item.get('is_video', False)
                start_t = float(cue.get('time_seconds', 0))
                duration = float(cue.get('duration_seconds', max(1.0, script_data.get('duration_seconds', self.config.video_duration_seconds) / max(1, len(slide_items)))))

                if is_video:
                    try:
                        vclip = VideoFileClip(path).set_start(start_t)
                        # If the video clip is longer than needed, subclip
                        if vclip.duration > duration:
                            vclip = vclip.subclip(0, duration).set_duration(duration)
                        else:
                            vclip = vclip.set_duration(duration)

                        # Resize to width and preserve aspect
                        try:
                            vclip = vclip.resize(width=W)
                        except Exception:
                            pass

                        # Gentle crossfade in
                        try:
                            vclip = vclip.crossfadein(min(0.35, duration * 0.2))
                        except Exception:
                            pass

                        clips.append(vclip)
                    except Exception:
                        # Fallback to image slide if video fails
                        img_clip = ImageClip(path).set_start(start_t).set_duration(duration)
                        try:
                            img_clip = img_clip.resize(width=W)
                        except Exception:
                            pass
                        clips.append(img_clip)
                else:
                    # Image or generated slide
                    img_clip = ImageClip(path).set_start(start_t).set_duration(duration)
                    try:
                        img_clip = img_clip.resize(width=W)
                    except Exception:
                        pass

                    # Apply subtle Ken Burns to images
                    try:
                        img_clip = img_clip.fx(vfx.resize, lambda t: 1 + 0.03 * (t / max(0.0001, duration)))
                    except Exception:
                        pass

                    try:
                        img_clip = img_clip.crossfadein(min(0.35, duration * 0.2))
                    except Exception:
                        pass

                    clips.append(img_clip)

                # Only display literal text overlays for cues with type 'text'
                if cue.get('type') == 'text' and int(start_t) == 0:
                    txt = cue.get('content', '')
                    try:
                        txt_clip = TextClip(txt, fontsize=72, color='white', stroke_color='black', stroke_width=2)
                        txt_clip = txt_clip.set_start(start_t).set_duration(min(3.0, duration)).set_position(('center', 80)).crossfadein(0.15)
                        clips.append(txt_clip)
                    except Exception:
                        pass

            # Add code overlays if this is a coding topic
            if is_coding and code_snippets:
                code_display_interval = max(2.0, total_duration / (len(code_snippets) + 1))
                for idx, code_snippet in enumerate(code_snippets[:3]):  # Max 3 code displays
                    code_start = 1.0 + (idx * code_display_interval)
                    if code_start < total_duration - 2.0:
                        try:
                            code_clip = add_code_overlay(None, code_snippet, min(3.0, code_display_interval - 0.5), ('center', 'bottom'))
                            if code_clip:
                                code_clip = code_clip.set_start(code_start)
                                clips.append(code_clip)
                        except Exception as e:
                            print(f"⚠️ Failed to add code overlay: {e}")

            # Build composite timeline using absolute starts
            total_duration = script_data.get('duration_seconds', self.config.video_duration_seconds)
            try:
                composite = CompositeVideoClip(clips, size=(W, H)).set_duration(total_duration)
            except Exception:
                # Fallback: naive concatenation if composition fails
                simple_clips = [c.set_start(0) for c in clips]
                composite = CompositeVideoClip(simple_clips, size=(W, H)).set_duration(total_duration)

            # Attach audio aligned to timeline
            try:
                audio = AudioFileClip(str(full_audio_path))
                composite = composite.set_audio(audio)
            except Exception as e:
                print(f"⚠️ Could not attach audio: {e}")

            # Export final video with detailed logging
            import logging
            logger = logging.getLogger(__name__)
            try:
                logger.info(f"🎥 Starting video file write to: {output_path}")
                logger.info(f"   Resolution: {W}x{H} @ {self.config.video_fps}fps, Duration: {total_duration}s")
                composite.write_videofile(
                    str(output_path),
                    fps=self.config.video_fps,
                    codec='libx264',
                    audio_codec='aac',
                    verbose=False,
                    logger=None  # Suppress moviepy's verbose logging
                )
                logger.info(f"✅ Video file write complete: {output_path}")
            except Exception as e:
                logger.error(f"❌ Video file write failed: {e}")
                raise

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
