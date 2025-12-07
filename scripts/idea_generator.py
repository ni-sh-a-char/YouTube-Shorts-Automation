# FILE: scripts/idea_generator.py
# Generate viral YouTube Shorts ideas using Google Gemini

import json
from typing import List, Dict, Any, Optional
from src.llm import generate as llm_generate
from scripts.config import get_config


class IdeaGenerator:
    """Generate viral YouTube Shorts ideas for tech/coding niche."""
    
    def __init__(self):
        """Initialize Gemini API."""
        config = get_config()
        # LLM provider is configurable (gemini or groq). Do not require Gemini specifically.
        self.config = config
    
    def generate_ideas(
        self,
        topic: str,
        num_ideas: int = 5,
        duration_seconds: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Generate viral YouTube Shorts ideas for a given topic.
        
        Args:
            topic: Coding/tech topic (e.g., "Python", "VS Code", "Git")
            num_ideas: Number of ideas to generate
            duration_seconds: Target video duration
            
        Returns:
            List of idea dictionaries
        """
        prompt = self._create_prompt(topic, num_ideas, duration_seconds)
        
        try:
            model_name = self.config.groq_model if self.config.llm_provider == 'groq' else self.config.gemini_model
            response = llm_generate(prompt, model=model_name)
            ideas = self._parse_response(response.text)
            return ideas[:num_ideas]
        except Exception as e:
            print(f"❌ ERROR: Failed to generate ideas for topic '{topic}': {e}")
            # Fallback: return a simple default idea so pipeline can continue
            fallback = {
                "id": 1,
                "title": f"Quick {topic} Tip",
                "duration_seconds": duration_seconds,
                "hook": f"One {topic} trick you should know.",
                "body": f"Here's a concise {topic} tip: keep it short and actionable.",
                "cta": "Try this today!",
                "visual_cues": "Show code snippet / terminal / highlighting",
                "keywords": f"{topic},Tip,Shorts",
                "difficulty": "beginner"
            }
            return [fallback]
    
    def _create_prompt(self, topic: str, num_ideas: int, duration: int) -> str:
        """
        Create Gemini prompt for idea generation.
        
        Args:
            topic: Tech topic
            num_ideas: Number of ideas to generate
            duration: Video duration in seconds (minimum 30)
            
        Returns:
            Formatted prompt
        """
        # Enforce minimum 30 seconds
        duration = max(duration, 30)

        # If the topic appears to be non-coding, explicitly instruct the model to avoid code
        try:
            from scripts.code_utils import is_coding_topic
            is_coding = is_coding_topic(topic)
        except Exception:
            is_coding = False

        avoid_coding_instruction = ""
        if not is_coding:
            avoid_coding_instruction = (
                "IMPORTANT: Do NOT include any code, code snippets, terminal output, IDE shots, or programming\ncommands. Create non-technical, general-audience ideas (e.g., lifestyle, productivity, finance, health,\ncreativity, quick tips) instead."
            )

        return f"""You are a viral YouTube Shorts content creator.

{avoid_coding_instruction}

Generate {num_ideas} engaging and viral YouTube Shorts ideas about "{topic}" suitable for a broad audience.

Each idea should:
1. Be suitable for a {duration}-second video
2. Start with a compelling hook (first 2 seconds)
3. Include a concise, non-technical tip or insight
4. End with a clear call-to-action or takeaway
5. Include specific visual suggestions (text overlay, b-roll, stock clips, photos, or simple motion graphics)

Format your response as a JSON array with exactly {num_ideas} objects. Each object must have these keys:
- "id": unique ID (integer 1-{num_ideas})
- "title": catchy short title (max 50 chars)
- "duration_seconds": {duration}
- "hook": compelling opening (max 100 chars, appears first 2 seconds)
- "body": main tip/trick/insight (max 300 chars)
- "cta": call-to-action or conclusion (max 100 chars)
- "visual_cues": suggested visual elements (describe footage, b-roll, text overlays, or animations)
- "keywords": comma-separated keywords for this idea
- "difficulty": beginner, intermediate, or advanced

Return ONLY valid JSON, starting with [ and ending with ]. Do not include markdown code blocks.

Example format (not the actual content):
[
    {{
        "id": 1,
        "title": "One-Minute Morning Routine to Boost Energy",
        "duration_seconds": {duration},
        "hook": "Want more energy before your coffee?",
        "body": "Try this 1-minute stretch and breathing routine to feel energized and focused.",
        "cta": "Try this tomorrow morning!",
        "visual_cues": "person stretching, close-up of breath, text-overlay steps",
        "keywords": "morning routine, energy, wellness",
        "difficulty": "beginner"
    }}
]
"""
    
    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Gemini response and extract ideas.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            List of parsed ideas
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
            ideas = json.loads(json_str)
            
            # Validate structure
            if not isinstance(ideas, list):
                raise ValueError("Response is not a JSON array")
            
            # Ensure all required fields are present
            for idea in ideas:
                self._validate_idea(idea)
            
            return ideas
        
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Gemini response as JSON: {e}")
            print(f"   Response: {response_text[:200]}...")
            raise
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            raise
    
    def _validate_idea(self, idea: Dict[str, Any]) -> None:
        """
        Validate idea structure.
        
        Args:
            idea: Idea dictionary to validate
            
        Raises:
            ValueError if validation fails
        """
        required_keys = ['id', 'title', 'hook', 'body', 'cta', 'visual_cues']
        missing = [k for k in required_keys if k not in idea]
        
        if missing:
            raise ValueError(f"Idea missing required keys: {missing}")
    
    def generate_batch_ideas(
        self,
        topics: Optional[List[str]] = None,
        ideas_per_topic: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate ideas for multiple topics.
        
        Args:
            topics: List of topics (uses config if not provided)
            ideas_per_topic: Number of ideas per topic
            
        Returns:
            Dictionary mapping topics to their ideas
        """
        if topics is None:
            topics = self.config.topics_rotation

        # Filter out coding/programming topics if present — user requested non-coding content
        coding_keywords = ['code', 'python', 'javascript', 'java', 'programming', 'developer', 'dev', 'git', 'vscode', 'terminal', 'bash', 'linux']
        filtered = [t for t in topics if not any(kw in t.lower() for kw in coding_keywords)]
        if not filtered:
            # If all provided topics are coding, fall back to a set of non-coding topics
            filtered = ['productivity', 'life hacks', 'mental health', 'personal finance', 'cooking hacks', 'travel tips', 'creativity']

        topics = filtered
        
        all_ideas = {}
        
        for topic in topics:
            print(f"🤖 Generating ideas for topic: {topic}")
            try:
                ideas = self.generate_ideas(
                    topic=topic,
                    num_ideas=ideas_per_topic,
                    duration_seconds=self.config.video_duration_seconds,
                )
                all_ideas[topic] = ideas
                print(f"✅ Generated {len(ideas)} ideas for {topic}")
            except Exception as e:
                print(f"⚠️ Failed to generate ideas for {topic}: {e}")
                all_ideas[topic] = []
        
        return all_ideas


def generate_ideas_for_topic(
    topic: str,
    num_ideas: int = 5,
) -> List[Dict[str, Any]]:
    """
    Convenience function to generate ideas for a single topic.
    
    Args:
        topic: Coding/tech topic
        num_ideas: Number of ideas to generate
        
    Returns:
        List of ideas
    """
    generator = IdeaGenerator()
    return generator.generate_ideas(topic, num_ideas)


if __name__ == '__main__':
    # Test idea generation
    import sys
    
    topic = sys.argv[1] if len(sys.argv) > 1 else 'Python'
    
    print(f"🚀 Generating YouTube Shorts ideas for: {topic}")
    generator = IdeaGenerator()
    
    try:
        ideas = generator.generate_ideas(topic=topic, num_ideas=5)
        
        print(f"\n✅ Generated {len(ideas)} ideas:\n")
        
        for idea in ideas:
            print(f"📌 Idea {idea['id']}: {idea['title']}")
            print(f"   Hook: {idea['hook']}")
            print(f"   Body: {idea['body']}")
            print(f"   CTA: {idea['cta']}")
            print(f"   Visual: {idea['visual_cues']}")
            print(f"   Keywords: {idea.get('keywords', 'N/A')}")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
