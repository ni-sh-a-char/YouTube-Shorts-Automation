import json
import sys
from pathlib import Path
# Ensure project root is on sys.path so package imports work when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.short_script_creator import create_script_from_idea

example_idea = {
    "id": 1,
    "title": "Merge two dicts in one line",
    "duration_seconds": 30,
    "hook": "Merge dicts instantly",
    "body": "Combine two Python dictionaries into a new one using a single expression.",
    "cta": "Try this in your editor!",
}

if __name__ == '__main__':
    script = create_script_from_idea(example_idea, topic='Python')
    print(json.dumps(script, indent=2, ensure_ascii=False))
