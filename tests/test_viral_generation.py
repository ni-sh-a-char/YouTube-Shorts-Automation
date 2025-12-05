import os
import json
from scripts.short_script_creator import ShortScriptCreator
from scripts.video_editor import VideoEditor


def test_generate_viral_short():
    os.environ['VIRAL_FORMAT'] = 'true'

    idea = {
        'id': 'test1',
        'title': "Productivity hack you didn't know",
        'hook': "This one habit saves hours",
        'body': "A 2-minute reset that clears context switching and boosts focus.",
        'cta': "Try it tomorrow and see the difference",
        'difficulty': 'beginner'
    }

    creator = ShortScriptCreator()
    script = creator.create_script(idea, topic='productivity', duration_seconds=30)

    print('\n=== SCRIPT JSON ===')
    print(json.dumps(script, indent=2))

    # Try to run the video pipeline; if environment lacks ffmpeg or TTS, skip gracefully
    try:
        editor = VideoEditor()
        out_file = 'data/output/videos/test_productivity_short.mp4'
        print('\nAttempting to render video (may fail in CI without ffmpeg/TTS)...')
        video_path = editor.create_shorts_video(script, captions_srt_path=None, thumbnail_path=None, title=idea['title'], output_file=out_file)
        print('\nVideo created at:', video_path)
    except Exception as e:
        print('\nVideo creation skipped/failed:', e)


if __name__ == '__main__':
    test_generate_viral_short()
