# FILE: scripts/short_script_creator.py
# Convert viral ideas into optimized YouTube Shorts scripts

import sys
import json
import logging
from typing import Dict, Any, Optional

# Fix UTF-8 encoding for Windows terminals
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.llm import generate as llm_generate
from scripts.config import get_config
from scripts.utils import extract_keywords

# Setup logger
logger = logging.getLogger(__name__)


class ShortScriptCreator:
    """Create YouTube Shorts-optimized scripts from ideas."""
    
    def __init__(self):
        """Initialize Gemini API."""
        config = get_config()
        # We no longer require Gemini specifically; the LLM provider is configurable.
        self.config = config
    
    def create_script(
        self,
        idea: Dict[str, Any],
        topic: str = '',
        duration_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a Shorts-optimized script from an idea.
        
        Args:
            idea: Idea dictionary from IdeaGenerator
            topic: Topic/category
            duration_seconds: Target duration (uses config if not provided)
            
        Returns:
            Script dictionary with script text, metadata, and visual cues
        """
        if duration_seconds is None:
            duration_seconds = self.config.video_duration_seconds
        
        prompt = self._create_prompt(idea, topic, duration_seconds)
        
        try:
            # Use the LLM adapter which supports both Gemini and Groq
            model_name = self.config.groq_model if self.config.llm_provider == 'groq' else self.config.gemini_model
            response = llm_generate(prompt, model=model_name)
            script_data = self._parse_response(response.text, duration_seconds, idea)
            return script_data
        except Exception as e:
            print(f"❌ ERROR: Failed to create script for idea '{idea.get('title')}': {e}")
            # User requested to be notified if Gemini fails, rather than using a fallback.
            raise RuntimeError(f"Gemini API Error: {e}. Please check your API key.")


            # Build sections: Hook, 3 points with examples, Short demo/example, CTA
            hook = idea.get('hook') or f"Stop doing this in {topic}!"
            body = idea.get('body') or f"Here is a critical tip about {topic} that you need to know."
            cta = idea.get('cta') or 'Subscribe for more coding tips!'

            # Create a more structured fallback script
            script_parts = [
                f"{hook} [PAUSE]",
                f"Many developers struggle with {topic}, but here is the fix.",
                f"{body}",
                "Let me show you how it works in practice. [PAUSE]",
                "Notice how much cleaner this code is?",
                "This simple change can save you hours of debugging.",
                f"{cta}"
            ]
            
            # Join and pad if necessary
            script_text = " ".join(script_parts)
            current_words = len(script_text.split())
            
            if current_words < estimated_words:
                 padding = "It really is that simple. Try it out in your next project and see the difference."
                 script_text += f" {padding}"

            # Create visual cues
            visual_cues = [
                {"time_seconds": 0, "cue": f"Big Red Text: {hook}"},
                {"time_seconds": 5, "cue": "Screen recording of code editor"},
                {"time_seconds": 15, "cue": "Highlighting the fix in code"},
                {"time_seconds": 25, "cue": "Arrow pointing to Subscribe button"}
            ]

            return {
                "script": script_text,
                "duration_seconds": duration_seconds,
                "estimated_word_count": estimated_words,
                "visual_cues": visual_cues,
                "keywords": extract_keywords(script_text),
                "reading_notes": "Urgent, high energy.",
                "difficulty": idea.get('difficulty','beginner')
            }
    
    def _create_prompt(
        self,
        idea: Dict[str, Any],
        topic: str,
        duration: int,
    ) -> str:
                """
                Create the LLM prompt for viral-style short script generation.

                Returns a string prompt configured for the requested duration.
                """
                # Estimate words: use slightly faster rate for Shorts
                estimated = self._estimate_word_count(duration)

                # Viral-style 30s Short structure prompt. Request explicit [PAUSE] tokens
                # and per-cue timing. Output must be valid JSON only and follow the
                # exact schema described.
                # IMPORTANT: The model must NOT reference code that isn't present in the
                # video. Do NOT use phrases like "see code below", "I'll show the code",
                # or "code sample below" unless the environment variable
                # `ALLOW_CODE_IN_DESCRIPTION` is set to true. If code cannot be provided,
                # do not mention it.
                return f"""You are a top-tier short-form creator and growth marketer. Produce a voice-first, 30-second YouTube Short script optimized for attention, retention, and virality.
Output JSON only. Produce a single JSON object with keys: "script", "duration_seconds", "estimated_word_count", "visual_cues", "keywords", "reading_notes", "difficulty", "marketing_title", "description_for_upload", "seo_hashtags".

Constraints (follow exactly):
- Total `duration_seconds`: {duration} (do not change).
- `script`: Spoken-first narration. Structure it into three beats:
    1) HOOK (0–3s): One gripping sentence (emotion, surprise, or fact). End with [PAUSE].
    2) CORE MESSAGE (4–20s): 3–5 short sentences (each 4–10 words). Put [PAUSE] between each sentence.
    3) PAYOFF / CTA (21–30s): 1–2 sentences that transform or call-to-action. End with [PAUSE].
- Use [PAUSE] tokens to indicate intentional breath/pause points for TTS.
- `estimated_word_count`: integer, approx {estimated} words.

Visual cues:
- Provide `visual_cues` as a list of objects with keys: `time_seconds` (number), `duration_seconds` (number), `type` (one of "text","b-roll","screenshot","image"), `content` (short on-screen text or description), and optional `transition` ("fade","zoom","slide").
- Visual cues must align with the narration and cover each beat. Vary types across the video.

Reading notes:
- Provide `reading_notes` with speaking_rate ("normal"/"slower"), tone (e.g., "confident"), and emphasize words/phrases separated by commas.

Keywords & difficulty:
- Provide `keywords` array and `difficulty` string ("beginner"/"intermediate").

SEO & marketing fields (important):
- `marketing_title`: A sticky, curiosity-driven title under 60 characters optimized for click-throughs. Include 1 emoji if helpful.
- `description_for_upload`: A ready-to-paste YouTube description (max 5000 chars). Include a 1-2 sentence summary, a short CTA, and a list of hashtags (space-separated). If you cannot include code, do NOT mention code in this field.
- `seo_hashtags`: Provide a short array of 6-12 high-impact hashtags (no spaces in tags) prioritized by relevance.

Safety & code policy:
- DO NOT include or promise code unless `ALLOW_CODE_IN_DESCRIPTION` is enabled. If enabled, include a very short (<=10 lines) code snippet string under `code_snippet` (escaped) and include it in `description_for_upload`. Otherwise, never refer to code or say it will be shown.

Input Idea:
Title: {idea.get('title')}
Hook Concept: {idea.get('hook')}
Core Value: {idea.get('body')}
CTA: {idea.get('cta')}

Example minimal `visual_cues` item:
{{"time_seconds":0, "duration_seconds":3, "type":"text", "content":"⚡ QUICK TECH HACK", "transition":"zoom"}}

Return only the JSON object. No commentary, no markdown, exact JSON shape requested."""

    def _estimate_word_count(self, duration_seconds: int) -> int:
        """Estimate word count for voiceover duration."""
        # Average speech rate: 130-150 words per minute
        # Use 140 WPM as average
        # Ensure minimum 30 seconds
        duration_seconds = max(duration_seconds, 30)
        return int((duration_seconds / 60) * 140)
    
    def _parse_response(
        self,
        response_text: str,
        duration_seconds: int,
        idea: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Parse Gemini response and extract script data.
        
        Args:
            response_text: Raw response from Gemini
            duration_seconds: Target duration
            idea: Original idea dictionary (for topic detection)
            
        Returns:
            Parsed script data
        """
        try:
            # Clean up response and extract JSON
            json_str = response_text.strip()

            if json_str.startswith('```'):
                json_str = json_str.split('```')[1]
                if json_str.startswith('json'):
                    json_str = json_str[4:]
                json_str = json_str.strip()

            script_data = json.loads(json_str)

            # Post-process script to remove any direct references to code
            # (e.g., "see code below", "I'll show the code", code blocks, etc.)
            try:
                import re
                from scripts.code_utils import sanitize_script_for_topic, is_coding_topic, extract_code_markers
                
                script_text = script_data.get('script', '')
                topic = idea.get('title', '') if (idea and isinstance(idea, dict)) else ''
                is_coding = is_coding_topic(topic)
                
                # Apply topic-aware sanitization
                script_text = sanitize_script_for_topic(script_text, is_coding=is_coding)
                
                if script_text:
                    script_data['script'] = script_text
                
                # Extract code markers from visual cues (if present)
                visual_cues = script_data.get('visual_cues', [])
                if visual_cues:
                    code_snippets = extract_code_markers(visual_cues)
                    if code_snippets and is_coding:
                        script_data['code_snippets'] = code_snippets
                
                # Mark topic type for downstream processing
                script_data['is_coding_topic'] = is_coding
            except Exception as e:
                # If sanitization fails, use original but log warning
                logger.warning(f"⚠️ Script sanitization failed: {e}, using original")
                pass

            # Required keys
            if 'script' not in script_data:
                raise ValueError("Response missing 'script' key")

            # Ensure duration is set
            script_data['duration_seconds'] = int(script_data.get('duration_seconds', duration_seconds))

            # Provide estimated_word_count if missing
            if not script_data.get('estimated_word_count'):
                script_data['estimated_word_count'] = self._estimate_word_count(script_data['duration_seconds'])

            # Ensure keywords
            if not script_data.get('keywords'):
                script_data['keywords'] = extract_keywords(script_data['script'])

            # Normalize visual_cues
            visual_cues = script_data.get('visual_cues') or []
            if not isinstance(visual_cues, list):
                visual_cues = []

            # If visual_cues provided but missing timing, derive timings from [PAUSE] split
            if visual_cues and all(('time_seconds' in v and 'duration_seconds' in v) for v in visual_cues):
                # keep as-is
                script_data['visual_cues'] = visual_cues
            else:
                # Build cues from narration by splitting on [PAUSE]
                chunks = [c.strip() for c in script_data['script'].split('[PAUSE]') if c.strip()]
                if not chunks:
                    chunks = [script_data['script'].strip()]

                # Compute durations proportional to word counts
                words = [len(c.split()) for c in chunks]
                total_words = sum(words) or 1
                cues = []
                current_t = 0.0
                for i, chunk in enumerate(chunks):
                    dur = max(0.5, (words[i] / total_words) * script_data['duration_seconds'])
                    cue_type = 'text' if i == 0 else ('b-roll' if i % 2 == 0 else 'image')
                    cues.append({
                        'time_seconds': round(current_t, 2),
                        'duration_seconds': round(dur, 2),
                        'type': cue_type,
                        'content': (chunk[:120]).strip(),
                        'transition': 'fade' if i > 0 else 'zoom'
                    })
                    current_t += dur

                # Normalize final cue durations to fit exactly into total duration
                if cues:
                    last = cues[-1]
                    overflow = current_t - script_data['duration_seconds']
                    if overflow > 0:
                        last['duration_seconds'] = max(0.5, last['duration_seconds'] - overflow)

                script_data['visual_cues'] = cues

            # Final safety: ensure visual_cues types are within allowed set
            allowed = {'text', 'b-roll', 'screenshot', 'image'}
            for v in script_data['visual_cues']:
                if v.get('type') not in allowed:
                    v['type'] = 'image'
            # Ensure keywords are present; re-extract if missing or empty
            if not script_data.get('keywords'):
                try:
                    from scripts.utils import extract_keywords
                    script_data['keywords'] = extract_keywords(script_data.get('script', ''))
                except Exception:
                    script_data['keywords'] = []

            return script_data
        
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse response as JSON: {e}")
            print(f"   Response: {response_text[:200]}...")
            raise
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            raise
    
    def create_scripts_batch(
        self,
        ideas: Dict[str, list],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create scripts for a batch of ideas.
        
        Args:
            ideas: Dictionary mapping topics to lists of ideas
            
        Returns:
            Dictionary mapping idea IDs to script data
        """
        all_scripts = {}
        
        for topic, topic_ideas in ideas.items():
            print(f"📝 Creating scripts for {len(topic_ideas)} ideas in {topic}")
            
            for idea in topic_ideas:
                idea_id = f"{topic}_{idea.get('id')}"
                
                try:
                    script = self.create_script(idea, topic=topic)
                    all_scripts[idea_id] = script
                    print(f"✅ Created script for: {idea.get('title')}")
                except Exception as e:
                    print(f"⚠️ Failed to create script for {idea.get('title')}: {e}")
                    all_scripts[idea_id] = None
        
        return all_scripts


def create_script_from_idea(
    idea: Dict[str, Any],
    topic: str = '',
) -> Dict[str, Any]:
    """
    Convenience function to create script from idea.
    
    Args:
        idea: Idea dictionary
        topic: Topic/category
        
    Returns:
        Script data
    """
    creator = ShortScriptCreator()
    return creator.create_script(idea, topic)


if __name__ == '__main__':
    # Test script creation
    import sys
    
    # Example idea (would normally come from IdeaGenerator)
    example_idea = {
        "id": 1,
        "title": "Python List Trick That Saves Hours",
        "duration_seconds": 15,
        "hook": "Did you know this Python trick?",
        "body": "Use list comprehension instead of loops. It's faster and more readable.",
        "cta": "Try it in your next project!",
        "visual_cues": "Python code snippet, terminal output",
        "keywords": "Python, List Comprehension, Performance, Coding Tips",
        "difficulty": "beginner"
    }
    
    topic = "Python"
    
    print(f"📝 Creating YouTube Shorts script for idea: {example_idea['title']}")
    
    creator = ShortScriptCreator()
    
    try:
        script_data = creator.create_script(example_idea, topic=topic)
        
        print(f"\n✅ Script created successfully!\n")
        print(f"Script:\n{script_data['script']}\n")
        print(f"Duration: {script_data.get('duration_seconds', 'N/A')}s")
        print(f"Keywords: {', '.join(script_data.get('keywords', []))}")
        print(f"Visual Cues: {json.dumps(script_data.get('visual_cues', []), indent=2)}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
