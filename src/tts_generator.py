"""Text-to-speech helper for the Shorts pipeline.

This module selects a TTS provider based on the `TTS_PROVIDER` environment
variable. When `TTS_PROVIDER=gtts` the module will only use gTTS and will not
import or attempt to use `edge-tts` or other providers.

Supported providers:
 - gtts
 - edge-tts (optional, only used when explicitly selected)

If an unsupported provider is set, a warning is logged and gTTS is used.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def _get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        # Fall back to 'ffmpeg' on PATH
        return 'ffmpeg'


def _split_for_tts(text: str):
    if not text:
        return []
    parts = [p.strip() for p in text.split('[PAUSE]')]
    return [p for p in parts if p]


def _concatenate_audio(audio_paths: List[str], output_path: str) -> str:
    if not audio_paths:
        raise ValueError("No audio paths provided")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(audio_paths) == 1:
        import shutil
        shutil.copy(audio_paths[0], str(output_path))
        return str(output_path)

    concat_list = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    try:
        for path in audio_paths:
            safe_path = Path(path).absolute().as_posix().replace("'", "'\\''")
            concat_list.write(f"file '{safe_path}'\n")
        concat_list.flush()
        concat_list.close()

        ffmpeg_exe = _get_ffmpeg_exe()
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
        try:
            if os.path.exists(concat_list.name):
                os.remove(concat_list.name)
        except Exception:
            pass


# Determine provider at import time
_provider = os.getenv('TTS_PROVIDER', 'gtts').strip().lower()


if _provider in ('gtts', '', None):
    try:
        from gtts import gTTS
    except Exception as e:
        logger.error(f"gTTS is selected as TTS_PROVIDER but failed to import: {e}")
        raise


    def generate_voice(text: str, output_path: str = "data/audio/voice.mp3") -> str:
        """Generate audio using gTTS only.

        This function will NOT attempt to use edge-tts or any other provider.
        """
        if not text or not text.strip():
            raise ValueError("Input text is empty")

        out_path = Path(output_path)
        out_dir = out_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        chunks = _split_for_tts(str(text))
        if not chunks:
            chunks = [str(text).strip()]

        temp_files = []
        silence_tmp = None
        try:
            for idx, chunk in enumerate(chunks):
                safe_chunk = chunk.replace('[PAUSE]', ' ').strip()
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{idx}.mp3")
                tmp.close()
                tts = gTTS(text=safe_chunk, lang=os.getenv('TTS_LANGUAGE', 'en'), slow=False)
                tts.save(tmp.name)
                temp_files.append(tmp.name)

            # Create short silence file between chunks (400ms)
            ffmpeg_exe = _get_ffmpeg_exe()
            silence_tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_silence.mp3")
            silence_tmp.close()
            silence_dur = 0.4
            cmd = [ffmpeg_exe, '-y', '-f', 'lavfi', '-i', f"anullsrc=channel_layout=stereo:sample_rate=48000", '-t', str(silence_dur), '-q:a', '9', silence_tmp.name]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Interleave and concatenate
            concat_list = []
            for i, fpath in enumerate(temp_files):
                concat_list.append(fpath)
                if i < len(temp_files) - 1:
                    concat_list.append(silence_tmp.name)

            _concatenate_audio(concat_list, str(out_path))

            logger.info(f"✅ Voice generated: {out_path}")
            return str(out_path)

        except Exception as e:
            logger.error(f"❌ Error generating voice with gTTS: {e}")
            raise
        finally:
            for f in temp_files:
                try:
                    Path(f).unlink()
                except Exception:
                    pass
            if silence_tmp:
                try:
                    Path(silence_tmp.name).unlink()
                except Exception:
                    pass


elif _provider in ('edge', 'edge-tts'):
    # Import edge-tts lazily only when explicitly selected
    try:
        import asyncio
        import edge_tts
    except Exception as e:
        logger.error(f"edge-tts selected but failed to import: {e}")
        raise

    def _split_for_tts_edge(text: str):
        return _split_for_tts(text)

    async def _generate_voice_async_edge(text: str, output_path: str, voice: str = "en-US-ChristopherNeural") -> None:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def generate_voice(text: str, output_path: str = "data/audio/voice.mp3") -> str:
        if not text or not text.strip():
            raise ValueError("Input text is empty")

        out_path = Path(output_path)
        out_dir = out_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        VOICE = "en-US-ChristopherNeural"
        chunks = _split_for_tts_edge(str(text))
        if not chunks:
            chunks = [str(text).strip()]

        temp_files = []
        silence_tmp = None
        try:
            for idx, chunk in enumerate(chunks):
                safe_chunk = chunk.replace('[PAUSE]', ' ').strip()
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{idx}.mp3")
                tmp.close()
                asyncio.run(_generate_voice_async_edge(safe_chunk, tmp.name, VOICE))
                temp_files.append(tmp.name)

            ffmpeg_exe = _get_ffmpeg_exe()
            silence_tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_silence.mp3")
            silence_tmp.close()
            silence_dur = 0.4
            cmd = [ffmpeg_exe, '-y', '-f', 'lavfi', '-i', f"anullsrc=channel_layout=stereo:sample_rate=48000", '-t', str(silence_dur), '-q:a', '9', silence_tmp.name]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            concat_list = []
            for i, fpath in enumerate(temp_files):
                concat_list.append(fpath)
                if i < len(temp_files) - 1:
                    concat_list.append(silence_tmp.name)

            _concatenate_audio(concat_list, str(out_path))

            logger.info(f"✅ Voice generated: {out_path}")
            return str(out_path)

        except Exception as e:
            logger.error(f"❌ Error generating voice with edge-tts: {e}")
            raise
        finally:
            for f in temp_files:
                try:
                    Path(f).unlink()
                except Exception:
                    pass
            if silence_tmp:
                try:
                    Path(silence_tmp.name).unlink()
                except Exception:
                    pass


else:
    # Unsupported provider set — warn and fall back to gTTS implementation
    logger.warning(f"Unsupported TTS_PROVIDER '{_provider}' — falling back to gTTS")
    try:
        from gtts import gTTS
    except Exception as e:
        logger.error(f"gTTS import failed while falling back: {e}")
        raise

    def generate_voice(text: str, output_path: str = "data/audio/voice.mp3") -> str:
        # Reuse gTTS implementation
        if not text or not text.strip():
            raise ValueError("Input text is empty")

        out_path = Path(output_path)
        out_dir = out_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        chunks = _split_for_tts(str(text))
        if not chunks:
            chunks = [str(text).strip()]

        temp_files = []
        silence_tmp = None
        try:
            for idx, chunk in enumerate(chunks):
                safe_chunk = chunk.replace('[PAUSE]', ' ').strip()
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{idx}.mp3")
                tmp.close()
                tts = gTTS(text=safe_chunk, lang=os.getenv('TTS_LANGUAGE', 'en'), slow=False)
                tts.save(tmp.name)
                temp_files.append(tmp.name)

            ffmpeg_exe = _get_ffmpeg_exe()
            silence_tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_silence.mp3")
            silence_tmp.close()
            silence_dur = 0.4
            cmd = [ffmpeg_exe, '-y', '-f', 'lavfi', '-i', f"anullsrc=channel_layout=stereo:sample_rate=48000", '-t', str(silence_dur), '-q:a', '9', silence_tmp.name]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            concat_list = []
            for i, fpath in enumerate(temp_files):
                concat_list.append(fpath)
                if i < len(temp_files) - 1:
                    concat_list.append(silence_tmp.name)

            _concatenate_audio(concat_list, str(out_path))

            logger.info(f"✅ Voice generated: {out_path}")
            return str(out_path)

        except Exception as e:
            logger.error(f"❌ Error generating voice with fallback gTTS: {e}")
            raise
        finally:
            for f in temp_files:
                try:
                    Path(f).unlink()
                except Exception:
                    pass
            if silence_tmp:
                try:
                    Path(silence_tmp.name).unlink()
                except Exception:
                    pass
