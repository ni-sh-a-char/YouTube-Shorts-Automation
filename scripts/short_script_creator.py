# FILE: scripts/short_script_creator.py
# Convert viral ideas into optimized YouTube Shorts scripts

import json
from typing import Dict, Any, Optional
from src.llm import generate as llm_generate
from scripts.config import get_config
from scripts.utils import extract_keywords


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
            script_data = self._parse_response(response.text, duration_seconds)
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
        Create Gemini prompt for script generation.
        
        Args:
            idea: Idea dictionary
            topic: Topic
            duration: Video duration
            
        Returns:
            Formatted prompt
        """
        # Target ~150 words per minute. For 30s, that's ~75 words.
        # We want a bit more density for Shorts, so ~160 wpm.
        word_count = int((duration / 60) * 160)

        # Speakable prompt template: short sentences, explicit [PAUSE] tokens,
        # narration separated from on-screen code. Output JSON only.
        return f"""You are a friendly, clear presenter creating a spoken script for a {duration}-second YouTube Short.
Output JSON only. Produce a single object with keys: "script", "duration_seconds", "estimated_word_count", "visual_cues", "keywords", "reading_notes", "difficulty".

Input Idea:
Title: {idea.get('title')}
Hook Concept: {idea.get('hook')}
Core Value: {idea.get('body')}
CTA: {idea.get('cta')}

Strict rules (follow exactly):
1. Write the spoken `script` as plain text only. Use short sentences (8–14 words each). Use [PAUSE] to indicate a short pause. Avoid code blocks or markdown.
2. Provide `visual_cues` as a JSON list of objects with keys: `time_seconds` (number), `type` ("text"|"code"|"screenshot"), and `content` (string). `content` is what appears on-screen; keep it concise.
3. When showing code: explain the idea in plain English first in the narration, then include the exact code in a `visual_cues` entry with `type":"code"`.
   - Do NOT read punctuation verbatim in the narration; instead describe code plainly. Keep code short (single line when possible).
4. Hook: one high-impact short sentence at the start (<=8 words).
5. Include one concrete example, shown visually and explained verbally with 1–2 short sentences.
6. Provide `reading_notes` with: speaking_rate ("normal"/"slower"), tone, and which words to emphasize.
7. Estimated word count should be approximately {word_count} words.

Example output structure (generate exactly this shape):
{{
  "script": "Hook sentence. [PAUSE] Narration sentence. [PAUSE] ...",
  "duration_seconds": {duration},
  "estimated_word_count": {word_count},
  "visual_cues": [
    {{"time_seconds": 0, "type": "text", "content": "MERGE TWO DICTS IN 1 LINE"}},
    {{"time_seconds": 3, "type": "code", "content": "a = {{**x, **y}}"}},
    {{"time_seconds": 10, "type": "text", "content": "This creates a new dict 'a' containing keys from x and y."}}
  ],
  "keywords": ["python", "dict", "merge"],
  "reading_notes": "speaking_rate:normal; tone:confident; emphasize:'one line','merge'",
  "difficulty": "beginner"
}}

Generate the JSON now. No markdown and no extra commentary."""

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
    ) -> Dict[str, Any]:
        """
        Parse Gemini response and extract script data.
        
        Args:
            response_text: Raw response from Gemini
            duration_seconds: Target duration
            
        Returns:
            Parsed script data
        """
        try:
            # Clean up response
            json_str = response_text.strip()
            
            # Remove markdown code blocks if present
            if json_str.startswith('```'):
                json_str = json_str.split('```')[1]
                if json_str.startswith('json'):
                    json_str = json_str[4:]
                json_str = json_str.strip()
            
            # Parse JSON
            script_data = json.loads(json_str)
            
            # Validate structure
            required_keys = ['script', 'duration_seconds', 'visual_cues']
            missing = [k for k in required_keys if k not in script_data]
            
            if missing:
                raise ValueError(f"Response missing required keys: {missing}")
            
            # Ensure visual_cues is a list
            if not isinstance(script_data.get('visual_cues'), list):
                script_data['visual_cues'] = []
            
            # Extract keywords if not provided
            if not script_data.get('keywords'):
                script_data['keywords'] = extract_keywords(script_data['script'])
            
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
