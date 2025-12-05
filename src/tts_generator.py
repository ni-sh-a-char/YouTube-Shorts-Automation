"""edge-tts based text-to-speech helper for the Shorts pipeline.

Provides `generate_voice(text, output_path)` using Microsoft Edge's online TTS service
for high-quality, natural-sounding voiceovers.
"""
import os
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import List
import edge_tts
import imageio_ffmpeg
from xml.sax.saxutils import escape as xml_escape

def get_ffmpeg_exe():
    """Get the path to the embedded ffmpeg executable."""
    return imageio_ffmpeg.get_ffmpeg_exe()

async def _generate_voice_async(text: str, output_path: str, voice: str = "en-US-ChristopherNeural") -> None:
    """Async helper to generate voice."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_voice(text: str, output_path: str = "data/audio/voice.mp3") -> str:
    """Generate an MP3 voice file from `text` using edge-tts.

    Args:
        text: Text to synthesize.
        output_path: Where to save the final MP3 file.

    Returns:
        The string path to the saved MP3 file.
    """
    if not text or not text.strip():
        raise ValueError("Input text is empty")

    out_path = Path(output_path)
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use a high-quality male voice by default, can be configured later
    # Options: en-US-ChristopherNeural, en-US-EricNeural, en-US-GuyNeural
    VOICE = "en-US-ChristopherNeural"

    # If the script contains [PAUSE] tokens, convert to SSML <break/> tags
    # so the TTS engine inserts silence instead of speaking the word "pause".
    try:
        text_str = str(text)
        if "[PAUSE]" in text_str:
            parts = [xml_escape(p.strip()) for p in text_str.split('[PAUSE]')]
            # join with a 300ms break
            ssml_body = "<break time='300ms'/>".join(parts)
            ssml = f"<speak>{ssml_body}</speak>"
            asyncio.run(_generate_voice_async(ssml, str(out_path), VOICE))
        else:
            asyncio.run(_generate_voice_async(text_str, str(out_path), VOICE))

        # Verify file exists and has size
        if not out_path.exists() or out_path.stat().st_size == 0:
            raise RuntimeError("Generated audio file is empty or missing")

        print(f"✅ Voice generated: {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"❌ Error generating voice with edge-tts: {e}")
        # Fallback to gTTS if edge-tts fails (e.g. network issues)
        print("⚠️ Falling back to gTTS (will remove [PAUSE] tokens)...")
        try:
            from gtts import gTTS
            safe_text = str(text).replace('[PAUSE]', ' ')
            tts = gTTS(text=safe_text, lang="en", slow=False)
            tts.save(str(out_path))
            return str(out_path)
        except Exception as e2:
            print(f"❌ gTTS fallback also failed: {e2}")
            raise e

def concatenate_audio(audio_paths: List[str], output_path: str) -> str:
    """Concatenate multiple audio files using ffmpeg."""
    if not audio_paths:
        raise ValueError("No audio paths provided")
        
    if len(audio_paths) == 1:
        import shutil
        shutil.copy(audio_paths[0], output_path)
        return output_path

    # Create concat list file
    concat_list = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    try:
        for path in audio_paths:
            # Escape single quotes for ffmpeg concat demuxer
            safe_path = Path(path).absolute().as_posix().replace("'", "'\\''")
            concat_list.write(f"file '{safe_path}'\n")
        concat_list.flush()
        concat_list.close()

        ffmpeg_exe = get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list.name,
            "-c", "copy",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")
            
        return str(output_path)
        
    finally:
        if os.path.exists(concat_list.name):
            os.remove(concat_list.name)
