import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.idea_generator import IdeaGenerator
from scripts.short_script_creator import ShortScriptCreator
from src.uploader import generate_metadata_from_script

ig = IdeaGenerator()
ideas = ig.generate_ideas(topic='Python Tricks', num_ideas=1)
ssc = ShortScriptCreator()
script_data = ssc.create_script(ideas[0], topic='Python Tricks', duration_seconds=30)
meta = generate_metadata_from_script(script_data, topic='Python Tricks')
print('---DESCRIPTION---')
print(meta.get('description'))
print('---TAGS---')
print(meta.get('tags'))
