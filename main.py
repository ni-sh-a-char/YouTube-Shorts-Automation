import os
import json
import datetime
import time
import traceback
import sys
from pathlib import Path
from src.generator import (
    generate_curriculum,
    generate_lesson_content,
    text_to_speech,
    generate_visuals,
    create_video,
    YOUR_NAME
)
from src.uploader import upload_to_youtube

CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")
LESSONS_PER_RUN = 1

def get_content_plan():
    if not CONTENT_PLAN_FILE.exists():
        print("📄 content_plan.json not found. Generating new plan...")
        new_plan = generate_curriculum()
        with open(CONTENT_PLAN_FILE, 'w') as f:
            json.dump(new_plan, f, indent=2)
        print(f"✅ New curriculum saved to {CONTENT_PLAN_FILE}")
        return new_plan
    else:
        try:
            with open(CONTENT_PLAN_FILE, 'r') as f:
                plan = json.load(f)
            if not plan.get("lessons") or not isinstance(plan["lessons"], list):
                raise ValueError("⚠️ Invalid or empty lesson plan detected.")
            return plan
        except Exception as e:
            print(f"❌ ERROR loading existing plan: {e}. Regenerating...")
            new_plan = generate_curriculum()
            with open(CONTENT_PLAN_FILE, 'w') as f:
                json.dump(new_plan, f, indent=2)
            return new_plan


def update_content_plan(plan):
    with open(CONTENT_PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)



def produce_lesson_videos(lesson):
    print(f"\n▶️ Starting production for Lesson: '{lesson['title']}'")
    unique_id = f"{datetime.datetime.now().strftime('%Y%m%d')}_{lesson['chapter']}_{lesson['part']}"

    lesson_content = generate_lesson_content(lesson['title'])

    # --- LONG FORM VIDEO DISABLED FOR NOW (User requested single short) ---
    # print("\n--- Producing Long-Form Video ---")
    # ... (long form logic commented out)
    long_video_id = "SKIPPED_LONG_VIDEO" 

    print("\n--- Producing Short Video ---")
    # short_script = f"{lesson_content['short_form_highlight']}"
    short_script = (f"{lesson_content['short_form_highlight']}\n\n"
    f"Link to the full lesson is in the description below.")
    short_audio_mp3_path = OUTPUT_DIR / f"short_audio_{unique_id}.mp3"
    short_audio_path = text_to_speech(short_script, short_audio_mp3_path)

    short_slide_dir = OUTPUT_DIR / f"slides_short_{unique_id}"
    short_slide_content = {
        "title": "Quick Tip!",
        "content": f"{lesson_content['short_form_highlight']}\n\n#AI for developers by {YOUR_NAME}"
    }
    short_slide_path = generate_visuals(
        output_dir=short_slide_dir,
        video_type='short',
        slide_content=short_slide_content,
        slide_number=1,
        total_slides=1
    )

    short_video_path = OUTPUT_DIR / f"short_video_{unique_id}.mp4"
    print(f"🎥 Creating short video at: {short_video_path}")
    create_video([short_slide_path], [short_audio_path], short_video_path, 'short')

    short_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type='short',
        thumbnail_title=f"Quick Tip: {lesson['title']}"
    )

    print("\n📤 Uploading to YouTube...")
    hashtags = lesson_content.get("hashtags", "#AI #Developer #LearnAI")
    
    highlight = (lesson_content.get('short_form_highlight') or '').strip()
    if not highlight:
        highlight = f"AI Quick Tip: {lesson['title']}"
    short_title = f"{highlight[:90].rstrip()} #Shorts"
    
    short_desc = (f"{lesson_content['short_form_highlight']}\n\n"
                  f"Subscribe for more from {YOUR_NAME}!\n\n"
                  f"{hashtags}")
    
    video_id = upload_to_youtube(
        short_video_path,
        short_title.strip(),
        short_desc,
        "AI,Shorts,TechTip",
        short_thumb_path
    )
    return video_id


def main():
    print("🚀 Starting Autonomous AI Course Generator")
    print(f"📁 Current working dir: {os.getcwd()}")
    print(f"📁 OUTPUT_DIR: {OUTPUT_DIR.resolve()}")

    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        print(f"📁 Created output folder: {OUTPUT_DIR.exists()}")
        plan = get_content_plan()
        pending = [(i, lesson) for i, lesson in enumerate(plan['lessons']) if lesson['status'] == 'pending']

        if not pending:
            print("🎉 All lessons produced! Generating new content plan to restart from scratch...")

            previous_titles = [lesson['title'] for lesson in plan['lessons']]
            new_plan = generate_curriculum(previous_titles=previous_titles)  # 🔁 Pass prior titles
            update_content_plan(new_plan)
            plan = new_plan
            pending = [(i, lesson) for i, lesson in enumerate(new_plan['lessons']) if lesson['status'] == 'pending']
            if not pending:
                print("⚠️ Curriculum generated but no valid lessons found.")
                return

        for lesson_index, lesson in pending[:LESSONS_PER_RUN]:
            try:
                video_id = produce_lesson_videos(lesson)
                if video_id:
                    for original_lesson in plan['lessons']:
                        if original_lesson['title'].strip().lower() == lesson['title'].strip().lower():
                            original_lesson['status'] = 'complete'
                            original_lesson['youtube_id'] = video_id
                            print(f"✅ Completed lesson: {lesson['title']}")
                            break
                    else:
                        print(f"⚠️ Could not find lesson in plan to mark as complete: {lesson['title']}")
                else:
                    print(f"⚠️ Upload failed: {lesson['title']}")
            except Exception as e:
                print(f"❌ Failed producing lesson: {lesson['title']}")
                traceback.print_exc()
            finally:
                update_content_plan(plan)
                print("📦 Content plan updated.")
                print(f"✅ Updated content plan for lesson: {lesson['title']}")
    except Exception as e:
        print("❌ Critical error in main()")
        traceback.print_exc()

    try:
        for file in OUTPUT_DIR.glob("*.wav"):
            file.unlink()
            print(f"🧹 Deleted: {file}")
    except Exception as e:
        print(f"⚠️ Could not clean up .wav files: {e}")

if __name__ == "__main__":
    # Allow manual override to run the pipeline once: python main.py --run-once
    if '--run-once' in sys.argv or '-r' in sys.argv:
        print("🔁 Running one-time Shorts generation (manual override)")
        from scheduler import run_once_and_exit
        result = run_once_and_exit()
        print(f"Result: {result}")
        sys.exit(0 if result.get('status') == 'success' else 1)
    else:
        main()
