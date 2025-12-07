import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.idea_generator import IdeaGenerator
from scripts.short_script_creator import ShortScriptCreator

ig = IdeaGenerator()
ideas = ig.generate_ideas(topic='Python Tricks', num_ideas=1)
print('Idea:', ideas)
ssc = ShortScriptCreator()
script_data = ssc.create_script(ideas[0], topic='Python Tricks', duration_seconds=30)
print('\nSCRIPT KEYS:', list(script_data.keys()))
print('\nCODE SNIPPETS:', script_data.get('code_snippets'))
print('\nIS CODING:', script_data.get('is_coding_topic'))
print('\nDESCRIPTION FOR UPLOAD:', script_data.get('description_for_upload'))
print('\nSCRIPT TEXT:\n', script_data.get('script')[:500])
