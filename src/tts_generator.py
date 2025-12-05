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
import tempfile
import subprocess
from pathlib import Path

def get_ffmpeg_exe():
    """Get the path to the embedded ffmpeg executable."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def split_for_tts(text: str):
    """Split text on [PAUSE] markers for chunked TTS generation.

    Returns list of trimmed chunks.
    """
    if not text:
        return []
    parts = [p.strip() for p in text.split('[PAUSE]')]
    return [p for p in parts if p]

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

    VOICE = "en-US-ChristopherNeural"

    chunks = split_for_tts(str(text))
    # If no explicit pauses, treat the whole text as one chunk
    if not chunks:
        chunks = [str(text).strip()]

    temp_files = []
    try:
        for idx, chunk in enumerate(chunks):
            # Use plain text for chunked generation (avoid sending SSML tags that
            # some engines may vocalize). Pauses are handled by inserting silence
            # files between chunks, so we send only readable text here.
            safe_chunk = chunk.replace('[PAUSE]', ' ').strip()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{idx}.mp3")
            tmp.close()
            try:
                asyncio.run(_generate_voice_async(safe_chunk, tmp.name, VOICE))
                temp_files.append(tmp.name)
            except Exception as e:
                # Fallback per-chunk to gTTS
                print(f"⚠️ edge-tts chunk failed ({e}), falling back to gTTS for chunk {idx}...")
                from gtts import gTTS
                tts = gTTS(text=safe_chunk, lang="en", slow=False)
                tts.save(tmp.name)
                temp_files.append(tmp.name)

        # Create a short silence file (400ms) to insert between chunks
        ffmpeg_exe = get_ffmpeg_exe()
        silence_tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_silence.mp3")
        silence_tmp.close()
        silence_dur = 0.4
        cmd = [ffmpeg_exe, '-y', '-f', 'lavfi', '-i', f"anullsrc=channel_layout=stereo:sample_rate=48000", '-t', str(silence_dur), '-q:a', '9', silence_tmp.name]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Interleave temp_files with silence files
        concat_list = []
        for i, fpath in enumerate(temp_files):
            concat_list.append(fpath)
            if i < len(temp_files) - 1:
                concat_list.append(silence_tmp.name)

        # Concatenate into final out_path
        concatenate_audio(concat_list, str(out_path))

        print(f"✅ Voice generated: {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"❌ Error generating voice: {e}")
        raise
    finally:
        # Cleanup temp files
        for f in temp_files:
            try:
                Path(f).unlink()
            except Exception:
                pass
        try:
            Path(silence_tmp.name).unlink()
        except Exception:
            pass

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
