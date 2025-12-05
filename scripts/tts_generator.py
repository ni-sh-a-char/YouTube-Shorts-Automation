# FILE: scripts/tts_generator.py
# Text-to-Speech generation for YouTube Shorts scripts

import os
import tempfile
from pathlib import Path
from typing import Optional, Literal
import requests

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

from scripts.config import get_config


def split_for_tts(script: str):
    """Split a script into chunks on the [PAUSE] token and clean whitespace.

    Returns a list of non-empty chunks in order.
    """
    if not script:
        return []
    parts = [p.strip() for p in script.split('[PAUSE]')]
    return [p for p in parts if p]


class TTSGenerator:
    """Generate voiceovers from text using TTS services."""
    
    def __init__(self):
        """Initialize TTS generator."""
        self.config = get_config()
        self.provider = self.config.tts_provider.lower()
        self.language = self.config.tts_language
        self.speed = self.config.tts_speed
    
    def generate_speech(
        self,
        text: str,
        output_path: Path,
        provider: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            provider: TTS provider ('gtts' or 'ttsmaker'), uses config if not provided
            
        Returns:
            Path to generated audio file, or None if failed
        """
        provider = provider or self.provider
        provider = provider.lower()
        
        print(f"🎤 Generating speech using {provider}...")
        
        try:
            # If the script includes [PAUSE] and pydub is available, synthesize
            # each chunk separately and concatenate with short silences for more
            # natural pacing in TTS.
            if '[PAUSE]' in text and AudioSegment is not None:
                return self._generate_with_pauses(text, output_path, provider)

            if provider == 'gtts':
                return self._generate_with_gtts(text, output_path)
            elif provider == 'ttsmaker':
                return self._generate_with_ttsmaker(text, output_path)
            else:
                print(f"⚠️ Unknown TTS provider: {provider}. Falling back to gTTS")
                return self._generate_with_gtts(text, output_path)

        except Exception as e:
            print(f"❌ ERROR: Failed to generate speech: {e}")
            return None

    def _generate_with_pauses(self, script: str, output_path: Path, provider: Optional[str]):
        """Generate speech for a script that contains [PAUSE] tokens.

        This method splits the script, generates per-chunk audio files, and
        concatenates them with short silences using pydub. Returns the final
        audio file path (MP3 by default).
        """
        provider = provider or self.provider
        chunks = split_for_tts(script)
        if not chunks:
            return None

        temp_dir = Path(tempfile.mkdtemp(prefix='tts_chunks_'))
        chunk_files = []

        try:
            for i, chunk in enumerate(chunks):
                chunk_path = temp_dir / f'chunk_{i}.mp3'
                # Use the underlying generator for each chunk but force mp3
                if provider == 'ttsmaker':
                    self._generate_with_ttsmaker(chunk, chunk_path)
                else:
                    # Default to gTTS for chunk generation
                    self._generate_with_gtts(chunk, chunk_path)
                if chunk_path.exists():
                    chunk_files.append(chunk_path)

            if not chunk_files:
                return None

            # Load all chunks and append 300ms silence between them
            silence = AudioSegment.silent(duration=300)
            final_audio = AudioSegment.empty()
            for i, fpath in enumerate(chunk_files):
                seg = AudioSegment.from_file(str(fpath))
                final_audio += seg
                if i < len(chunk_files) - 1:
                    final_audio += silence

            output_path.parent.mkdir(parents=True, exist_ok=True)
            mp3_path = output_path.with_suffix('.mp3')
            final_audio.export(str(mp3_path), format='mp3')

            # Convert to WAV if requested
            if output_path.suffix.lower() == '.wav':
                wav_path = self._mp3_to_wav(mp3_path)
                if wav_path:
                    mp3_path.unlink(missing_ok=True)
                    return wav_path
            return mp3_path

        finally:
            # Clean up temp chunk files
            for f in chunk_files:
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                temp_dir.rmdir()
            except Exception:
                pass
    
    def _generate_with_gtts(
        self,
        text: str,
        output_path: Path,
    ) -> Optional[Path]:
        """
        Generate speech using Google TTS (gTTS).
        
        Args:
            text: Text to convert
            output_path: Output path (should have .mp3 or .wav extension)
            
        Returns:
            Path to generated audio file, or None if failed
        """
        if gTTS is None:
            print("⚠️ gTTS not installed. Install with: pip install gtts")
            return None
        
        try:
            # Generate MP3
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mp3_path = output_path.with_suffix('.mp3')
            
            print(f"   Generating MP3 with gTTS...")
            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(str(mp3_path))
            
            # Convert to WAV if requested
            if output_path.suffix.lower() == '.wav':
                print(f"   Converting to WAV...")
                wav_path = self._mp3_to_wav(mp3_path)
                if wav_path:
                    # Remove temporary MP3
                    mp3_path.unlink(missing_ok=True)
                    return wav_path
                else:
                    # If conversion failed, return MP3
                    print(f"   ⚠️ MP3 to WAV conversion failed, returning MP3")
                    return mp3_path
            
            print(f"✅ Speech generated successfully: {mp3_path}")
            return mp3_path
        
        except Exception as e:
            print(f"❌ gTTS error: {e}")
            return None
    
    def _generate_with_ttsmaker(
        self,
        text: str,
        output_path: Path,
    ) -> Optional[Path]:
        """
        Generate speech using TTSMaker API.
        
        Args:
            text: Text to convert
            output_path: Output path
            
        Returns:
            Path to generated audio file, or None if failed
        """
        api_key = self.config.ttsmaker_api_key
        
        if not api_key:
            print("⚠️ TTSMAKER_API_KEY not configured. Falling back to gTTS")
            return self._generate_with_gtts(text, output_path)
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Map speed to TTSMaker value
            speed_map = {'slow': '0.5', 'normal': '1.0', 'fast': '1.5'}
            speed_value = speed_map.get(self.speed, '1.0')
            
            # Call TTSMaker API
            print(f"   Calling TTSMaker API...")
            url = 'https://api.ttsmaker.com/v1/tts'
            
            payload = {
                'text': text,
                'voice_id': '0',  # Default voice
                'audio_format': 'mp3',
                'audio_speed': speed_value,
            }
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Save audio file
            mp3_path = output_path.with_suffix('.mp3')
            with open(mp3_path, 'wb') as f:
                f.write(response.content)
            
            # Convert to WAV if requested
            if output_path.suffix.lower() == '.wav':
                print(f"   Converting to WAV...")
                wav_path = self._mp3_to_wav(mp3_path)
                if wav_path:
                    mp3_path.unlink(missing_ok=True)
                    return wav_path
                else:
                    print(f"   ⚠️ MP3 to WAV conversion failed, returning MP3")
                    return mp3_path
            
            print(f"✅ Speech generated successfully: {mp3_path}")
            return mp3_path
        
        except requests.exceptions.RequestException as e:
            print(f"❌ TTSMaker API error: {e}")
            print(f"   Falling back to gTTS")
            return self._generate_with_gtts(text, output_path)
        except Exception as e:
            print(f"❌ TTSMaker error: {e}")
            return None
    
    def _mp3_to_wav(self, mp3_path: Path) -> Optional[Path]:
        """
        Convert MP3 to WAV format.
        
        Args:
            mp3_path: Path to MP3 file
            
        Returns:
            Path to WAV file, or None if failed
        """
        if AudioSegment is None:
            print("⚠️ pydub not installed. Install with: pip install pydub")
            print("   Also requires ffmpeg: https://ffmpeg.org/download.html")
            return None
        
        try:
            wav_path = mp3_path.with_suffix('.wav')
            
            # Load MP3 and export as WAV
            audio = AudioSegment.from_mp3(str(mp3_path))
            audio.export(
                str(wav_path),
                format='wav',
                codec='pcm_s16le',  # 16-bit PCM
                parameters=['-q:a', '9', '-filter:a', 'volume=0.90']
            )
            
            print(f"✅ Converted to WAV: {wav_path}")
            return wav_path
        
        except Exception as e:
            print(f"❌ MP3 to WAV conversion failed: {e}")
            return None
    
    def generate_batch(
        self,
        texts: dict,
        output_dir: Path,
    ) -> dict:
        """
        Generate speech for multiple texts.
        
        Args:
            texts: Dictionary mapping IDs to text strings
            output_dir: Output directory
            
        Returns:
            Dictionary mapping IDs to audio file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_files = {}
        
        for text_id, text in texts.items():
            output_path = output_dir / f"audio_{text_id}.mp3"
            
            try:
                audio_path = self.generate_speech(text, output_path)
                if audio_path:
                    audio_files[text_id] = audio_path
                    print(f"✅ {text_id}: {audio_path}")
                else:
                    print(f"⚠️ {text_id}: Failed")
                    audio_files[text_id] = None
            except Exception as e:
                print(f"❌ {text_id}: {e}")
                audio_files[text_id] = None
        
        return audio_files


def generate_speech(
    text: str,
    output_path: Path,
    provider: str = 'gtts',
) -> Optional[Path]:
    """
    Convenience function to generate speech.
    
    Args:
        text: Text to convert to speech
        output_path: Output audio file path
        provider: TTS provider ('gtts' or 'ttsmaker')
        
    Returns:
        Path to generated audio file, or None if failed
    """
    generator = TTSGenerator()
    return generator.generate_speech(text, output_path, provider)


if __name__ == '__main__':
    # Test TTS generation
    import sys
    
    test_text = """Here's a Python trick that will blow your mind. 
    Use list comprehensions instead of loops. 
    It's faster and way more readable. 
    Try it in your next project!"""
    
    print("🎤 Testing TTS generation...")
    
    output_path = Path('test_audio.mp3')
    generator = TTSGenerator()
    
    try:
        audio_path = generator.generate_speech(test_text, output_path)
        
        if audio_path and audio_path.exists():
            size_mb = audio_path.stat().st_size / (1024 * 1024)
            print(f"✅ Audio generated: {audio_path} ({size_mb:.2f} MB)")
            # Clean up
            audio_path.unlink()
        else:
            print(f"❌ Failed to generate audio")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
