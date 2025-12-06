# FILE: src/generator.py
# FINAL, CLEAN VERSION: Compatible with per-slide audio sync, dynamic slides, and GitHub Actions.

import os
import json
import requests
import gc
from io import BytesIO
from src.llm import generate as llm_generate
from gtts import gTTS
from moviepy.editor import AudioFileClip, ImageClip, CompositeAudioClip, concatenate_videoclips, vfx
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
try:
    from pydub import AudioSegment
except Exception:
    AudioSegment = None

# --- Configuration ---
ASSETS_PATH = Path("assets")
FONT_FILE = ASSETS_PATH / "fonts/arial.ttf"
BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music/bg_music.mp3"
FALLBACK_THUMBNAIL_FONT = ImageFont.load_default()
YOUR_NAME = "ni_sh_a.char"
IS_RENDER = os.getenv('RENDER') is not None

# Adjust resolution for Render's 512MB limit
if IS_RENDER:
    # 720p is lighter on RAM (approx 45% of 1080p pixel count)
    SHORT_WIDTH, SHORT_HEIGHT = 720, 1280
    LONG_WIDTH, LONG_HEIGHT = 1280, 720
else:
    SHORT_WIDTH, SHORT_HEIGHT = 1080, 1920
    LONG_WIDTH, LONG_HEIGHT = 1920, 1080

# GitHub Actions compatibility for ImageMagick
if os.name == 'posix':
    change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})


def get_pexels_image(query, video_type):
    """Searches for a relevant image on Pexels and returns the image object."""
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        print("⚠️ PEXELS_API_KEY not found. Using solid color background.")
        return None

    orientation = 'landscape' if video_type == 'long' else 'portrait'
    try:
        headers = {"Authorization": pexels_api_key}
        params = {"query": f"abstract {query}", "per_page": 1, "orientation": orientation}
        response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get('photos'):
            image_url = data['photos'][0]['src']['large2x']
            image_response = requests.get(image_url, timeout=15)
            image_response.raise_for_status()
            return Image.open(BytesIO(image_response.content)).convert("RGBA")
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching Pexels image for query '{query}': {e}")
    except Exception as e:
        print(f"❌ General error fetching Pexels image for query '{query}': {e}")
    return None


def text_to_speech(text, output_path):
    """Wrapper for the new edge-tts generator. Cleans stage directions first."""
    import re
    from src.tts_generator import generate_voice
    
    # Remove stage directions like [PAUSE], (Smile), [Visual: ...]
    clean_text = re.sub(r'\[.*?\]', '', text)
    clean_text = re.sub(r'\(.*?\)', '', clean_text)
    
    return Path(generate_voice(clean_text, str(output_path)))


def generate_curriculum(previous_titles=None):
    """Generates the entire course curriculum using Gemini."""
    print("🤖 No content plan found. Generating a new curriculum from scratch...")
    try:
        # Use project LLM adapter (supports 'gemini' and 'groq')
        from scripts.config import get_config
        cfg = get_config()
        model_name = cfg.groq_model if cfg.llm_provider == 'groq' else cfg.gemini_model

        history = ""
        if previous_titles:
            formatted = "\n".join([f"{i+1}. {t}" for i, t in enumerate(previous_titles)])
            history = f"The following lessons have already been created:\n{formatted}\n\nPlease continue from where this series left off.\n"

        prompt = f"""
        You are an expert AI educator. Generate a curriculum for a YouTube series called 'AI for Developers by {YOUR_NAME}'.
        {history}
        The style must be: 'Assume the viewer is a beginner or non-technical person starting their journey into AI as a developer.
        Use simple real-world analogies, relatable examples, and then connect to technical concepts.'

        The curriculum must guide a developer from absolute beginner to advanced AI, covering foundations like Generative AI, LLMs, Vector Databases, and Agentic AI...
        ...then continue into deep AI topics like Reinforcement Learning, Transformers internals, multi-agent systems, tool use, LangGraph, AI architecture, and more.

        Respond with ONLY a valid JSON object. The object must contain a key "lessons" which is a list of 20 lesson objects.
        Each lesson object must have these keys: "chapter", "part", "title", "status" (defaulted to "pending"), and "youtube_id" (defaulted to null).
        """
        response = llm_generate(prompt, model=model_name)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        curriculum = json.loads(json_string)
        print("✅ New curriculum generated successfully!")
        return curriculum
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Failed to generate curriculum. {e}")
        raise


def generate_lesson_content(lesson_title):
    """Generates the content for one long-form lesson and its promotional short."""
    print(f"🤖 Generating content for lesson: '{lesson_title}'...")
    try:
        from scripts.config import get_config
        cfg = get_config()
        model_name = cfg.groq_model if cfg.llm_provider == 'groq' else cfg.gemini_model
        prompt = f"""
        You are creating a lesson for the 'AI for Developers by {YOUR_NAME}' series. The topic is '{lesson_title}'.
        The style is: Assume the viewer is a beginner developer or non-tech person who wants to learn AI from scratch.
        Use analogies and clear, simple language. Each concept must be explained from a developer's perspective, assuming no prior AI or ML knowledge.

        Generate a JSON response with three keys:
        1. "long_form_slides": A list of 7 to 8 slide objects for a longer, more detailed main video. Each object needs a "title" and "content" key.
        2. "short_form_highlight": A single, punchy, 1-2 sentence summary for a YouTube Short.
        3. "hashtags": A string of 5-7 relevant, space-separated hashtags for this lesson (e.g., "#GenerativeAI #LLM #Developer","#NeuralNetworks #BeginnerAI #AIforDevelopers").

        Return only valid JSON.
        """
        response = llm_generate(prompt, model=model_name)
        json_string = response.text.strip().replace("```json", "").replace("```", "")
        content = json.loads(json_string)
        print("✅ Lesson content generated successfully.")
        return content
    except Exception as e:
        print(f"❌ ERROR: Failed to generate lesson content: {e}")
        raise


def generate_visuals(output_dir, video_type, slide_content=None, thumbnail_title=None, slide_number=0, total_slides=0):
    """Generates a single professional, PPT-style slide or a thumbnail with corrected alignment."""
    output_dir.mkdir(exist_ok=True, parents=True)
    is_thumbnail = thumbnail_title is not None

    width, height = (LONG_WIDTH, LONG_HEIGHT) if video_type == 'long' else (SHORT_WIDTH, SHORT_HEIGHT)
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    bg_image = get_pexels_image(title, video_type)

    if not bg_image:
        # Create a more interesting fallback background (dark gradient)
        bg_image = Image.new('RGB', (width, height), color=(15, 23, 42)) # Slate-900
        draw_bg = ImageDraw.Draw(bg_image)
        # Draw some subtle grid lines for "tech" feel
        for x in range(0, width, 100):
            draw_bg.line([(x, 0), (x, height)], fill=(30, 41, 59), width=2)
        for y in range(0, height, 100):
            draw_bg.line([(0, y), (width, y)], fill=(30, 41, 59), width=2)
        
        bg_image = bg_image.convert("RGBA")

    bg_image = bg_image.resize((width, height)).filter(ImageFilter.GaussianBlur(5))
    darken_layer = Image.new('RGBA', bg_image.size, (0, 0, 0, 150))
    final_bg = Image.alpha_composite(bg_image, darken_layer).convert("RGB")

    if is_thumbnail and video_type == 'long':
        w, h = final_bg.size
        if h > w:
            print("⚠️ Detected vertical thumbnail for long video. Rotating and resizing...")
            final_bg = final_bg.transpose(Image.ROTATE_270).resize((width, height))

    draw = ImageDraw.Draw(final_bg)

    try:
        # Scale fonts slightly based on resolution
        scale_factor = width / 1080.0 if video_type == 'short' else width / 1920.0
        
        title_size = int((80 if video_type == 'long' else 90) * scale_factor)
        content_size = int((45 if video_type == 'long' else 55) * scale_factor)
        footer_size = int((25 if video_type == 'long' else 35) * scale_factor)

        title_font = ImageFont.truetype(str(FONT_FILE), title_size)
        content_font = ImageFont.truetype(str(FONT_FILE), content_size)
        footer_font = ImageFont.truetype(str(FONT_FILE), footer_size)
    except IOError:
        title_font = content_font = footer_font = FALLBACK_THUMBNAIL_FONT

    if not is_thumbnail:
        # Header background
        header_height = int(height * 0.18)
        draw.rectangle([0, 0, width, header_height], fill=(25, 40, 65, 200))

        # Wrap title text if needed
        words = title.split()
        title_lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            if bbox[2] - bbox[0] < width * 0.9:
                current_line = test_line
            else:
                title_lines.append(current_line)
                current_line = word
        title_lines.append(current_line)

        # Center vertically in header
        line_height = title_font.getbbox("A")[3] + 10
        total_title_height = len(title_lines) * line_height
        y_text = (header_height - total_title_height) / 2

        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            x = (width - (bbox[2] - bbox[0])) / 2
            draw.text((x, y_text), line, font=title_font, fill=(255, 255, 255))
            y_text += line_height
    else:
        # Center title on thumbnail
        bbox = draw.textbbox((0, 0), title, font=title_font)
        x = (width - (bbox[2] - bbox[0])) / 2
        y = (height - (bbox[3] - bbox[1])) / 2
        draw.text((x, y), title, font=title_font, fill=(255, 255, 255), stroke_width=2, stroke_fill="black")

    if not is_thumbnail:
        # Main content block
        content = slide_content.get("content", "")
        is_special_slide = len(content.split()) < 10

        words = content.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if draw.textbbox((0, 0), test_line, font=content_font)[2] < width * 0.85:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        line_height = content_font.getbbox("A")[3] + 15
        total_text_height = len(lines) * line_height
        y_text = (height - total_text_height) / 2 if is_special_slide else header_height + 100

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=content_font)
            x = (width - (bbox[2] - bbox[0])) / 2
            draw.text((x, y_text), line, font=content_font, fill=(230, 230, 230))
            y_text += line_height

        # Footer
        footer_height = int(height * 0.06)
        draw.rectangle([0, height - footer_height, width, height], fill=(25, 40, 65, 200))
        draw.text((40, height - footer_height + 12), f"AI for Developers by {YOUR_NAME}", font=footer_font, fill=(180, 180, 180))

        if total_slides > 0:
            slide_num_text = f"Slide {slide_number} of {total_slides}"
            bbox = draw.textbbox((0, 0), slide_num_text, font=footer_font)
            draw.text((width - bbox[2] - 40, height - footer_height + 12), slide_num_text, font=footer_font, fill=(180, 180, 180))

    file_prefix = "thumbnail" if is_thumbnail else f"slide_{slide_number:02d}"
    path = output_dir / f"{file_prefix}.png"
    final_bg.save(path)
    return str(path)


def get_pexels_video(query, orientation='portrait'):
    """Searches for a relevant video on Pexels and returns the video URL."""
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        print("⚠️ PEXELS_API_KEY not found. Using static background.")
        return None

    try:
        headers = {"Authorization": pexels_api_key}
        params = {"query": f"technology {query}", "per_page": 1, "orientation": orientation, "size": "medium"}
        response = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get('videos'):
            # Get the best quality video file that matches our needs
            video_files = data['videos'][0]['video_files']
            # Sort by quality/size
            video_files.sort(key=lambda x: x['width'] * x['height'], reverse=True)
            return video_files[0]['link']
    except Exception as e:
        print(f"❌ Error fetching Pexels video for query '{query}': {e}")
    return None


def create_caption_clips(script_text, duration, size=None):
    """Generates subtitle clips using PIL (no ImageMagick)."""
    # Default to current global short size if not provided
    if size is None:
        size = (SHORT_WIDTH, SHORT_HEIGHT)
    # Simple word-level timestamping (linear interpolation)
    words = script_text.replace('[PAUSE]', '').split()
    if not words:
        return []
        
    word_duration = duration / len(words)
    clips = []
    
    clips = []
    
    # Scale font
    font_size = int(80 * (size[0] / 1080.0))
    try:
        font = ImageFont.truetype(str(FONT_FILE), font_size)
    except:
        font = ImageFont.load_default()

    W, H = size
    
    for i, word in enumerate(words):
        start_time = i * word_duration
        end_time = (i + 1) * word_duration
        
        # Create transparent image with text
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Text styling
        text = word.upper()
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        x = (W - w) / 2
        y = (H - h) / 2
        
        # Shadow/Stroke
        stroke_width = 4
        draw.text((x, y), text, font=font, fill='white', stroke_width=stroke_width, stroke_fill='black')
        
        # Create clip
        txt_clip = (ImageClip(np.array(img))
                   .set_start(start_time)
                   .set_duration(end_time - start_time)
                   .set_position('center'))
                   
        clips.append(txt_clip)
        
    return clips


def create_video(slide_paths, audio_paths, output_path, video_type):
    """Creates a final video from slides/videos and audio."""
    print(f"🎬 Creating {video_type} video...")
    
    # Aggressive garbage collection
    gc.collect()
    
    # Ensure numpy is imported for PIL->MoviePy conversion
    global np
    import numpy as np
    
    try:
        if not slide_paths or not audio_paths:
            raise ValueError("No slides or audio provided.")

        # Load audio first to determine duration
        audio_clips = [AudioFileClip(str(p)) for p in audio_paths]
        full_audio = concatenate_videoclips([
            # Create dummy video clips just to hold audio, we'll extract audio later
            ImageClip(slide_paths[0] if slide_paths else "assets/placeholder.png").set_audio(a).set_duration(a.duration)
            for a in audio_clips
        ]).audio
        
        total_duration = full_audio.duration
        
        # Visuals
        visual_clips = []
        current_time = 0
        
        for i, (img_path, audio_clip) in enumerate(zip(slide_paths, audio_clips)):
            duration = audio_clip.duration
            
            # Check if we can get a video background for this segment
            # We'll use the slide text/title as query if possible, or just "coding"
            # For now, let's stick to the generated slide images but add a zoom effect
            
            img_clip = ImageClip(img_path).set_duration(duration)
            
            # Ken Burns Effect (Zoom In)
            # Resize from 100% to 110% over duration
            def zoom(t):
                scale = 1 + 0.1 * (t / duration)
                return scale
                
            # Apply zoom (requires resizing, which can be slow, so we keep it simple for now)
            # img_clip = img_clip.resize(zoom) 
            # Note: MoviePy resize with function is very slow. 
            # Alternative: Just static for now to ensure stability, or simple pan.
            
            visual_clips.append(img_clip)
            current_time += duration

        final_video = concatenate_videoclips(visual_clips, method="compose")
        final_video = final_video.set_audio(full_audio)

        # Background Music
        if BACKGROUND_MUSIC_PATH.exists():
            print("🎵 Adding background music...")
            bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.10) # Lower volume
            if bg_music.duration < total_duration:
                bg_music = bg_music.fx(vfx.loop, duration=total_duration)
            else:
                bg_music = bg_music.subclip(0, total_duration)
                
            final_audio = CompositeAudioClip([final_video.audio, bg_music])
            final_video = final_video.set_audio(final_audio)

        # Write file using imageio-ffmpeg
        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="128k" if IS_RENDER else "192k", # Lower bitrate for Render
            preset="ultrafast" if IS_RENDER else "medium", # Faster encoding = less buffer time often
            threads=1,
            logger=None # Reduce noise
        )
        print(f"✅ {video_type.capitalize()} video created successfully!")

    except Exception as e:
        print(f"❌ ERROR during video creation: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Explicit cleanup to free memory on Render
        try:
            if 'final_video' in locals(): final_video.close()
            if 'full_audio' in locals(): full_audio.close()
            if 'bg_music' in locals() and 'bg_music' in vars(): bg_music.close() # vars check for safety
            
            # Close all individual clips
            if 'audio_clips' in locals():
                for a in audio_clips: a.close()
            if 'visual_clips' in locals():
                for v in visual_clips: v.close()
                
            print("🧹 Released video resources")
        except Exception as cleanup_error:
            print(f"⚠️ Warning during cleanup: {cleanup_error}")
