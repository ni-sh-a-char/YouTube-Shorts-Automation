import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.uploader import generate_metadata_from_script
sd = {
  'script': 'Hook line.[PAUSE]Here is how you do it.\n\n```python\nprint("Hello World")\n```',
  'code_snippets': ['print("Hello World")'],
  'is_coding_topic': True,
  'keywords': ['python','example']
}
meta = generate_metadata_from_script(sd, topic='Python Tricks')
print('TITLE:', meta['title'])
print('\nDESCRIPTION:\n')
print(meta['description'])
