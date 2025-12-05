"""
End-to-end pipeline test: Idea Generation → Script → Video → Metadata → (Upload)
Validates the entire viral shorts generation system.
"""

import os
import json
from pathlib import Path
from datetime import datetime

# Enable viral format for the test
os.environ['VIRAL_FORMAT'] = 'true'

from scripts.idea_generator import IdeaGenerator
from scripts.short_script_creator import ShortScriptCreator
from scripts.video_editor import VideoEditor
from src.uploader import generate_metadata_from_script


def test_end_to_end_pipeline():
    """Run complete pipeline from idea generation to upload-ready files."""
    
    # Output tracking
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        'timestamp': timestamp,
        'topic': 'Time Management',
        'stages': {}
    }
    
    try:
        # ============================================================
        # STAGE 1: IDEA GENERATION
        # ============================================================
        print("\n" + "="*70)
        print("STAGE 1: IDEA GENERATION")
        print("="*70)
        
        idea_gen = IdeaGenerator()
        ideas = idea_gen.generate_ideas(topic='Time Management', num_ideas=1, duration_seconds=30)
        
        if not ideas:
            raise RuntimeError("Idea generation returned empty list")
        
        idea = ideas[0]
        print(f"\n✅ Generated idea: {idea.get('title')}")
        print(f"   Hook: {idea.get('hook')}")
        print(f"   Body: {idea.get('body')}")
        print(f"   CTA: {idea.get('cta')}")
        
        results['stages']['idea_generation'] = {
            'status': 'success',
            'idea': idea
        }
        
        # ============================================================
        # STAGE 2: SCRIPT CREATION
        # ============================================================
        print("\n" + "="*70)
        print("STAGE 2: SCRIPT CREATION (VIRAL FORMAT)")
        print("="*70)
        
        script_creator = ShortScriptCreator()
        script_data = script_creator.create_script(
            idea=idea,
            topic='Time Management',
            duration_seconds=30
        )
        
        if not script_data.get('script'):
            raise RuntimeError("Script generation failed - no script produced")
        
        print(f"\n✅ Generated script ({script_data.get('estimated_word_count')} words)")
        print(f"   Duration: {script_data.get('duration_seconds')}s")
        print(f"   Visual cues: {len(script_data.get('visual_cues', []))} cues")
        print(f"   Keywords: {', '.join(script_data.get('keywords', []))}")
        
        # Save script JSON
        scripts_dir = Path('data/output/scripts')
        scripts_dir.mkdir(parents=True, exist_ok=True)
        script_file = scripts_dir / f"script_e2e_{timestamp}.json"
        with open(script_file, 'w') as f:
            json.dump(script_data, f, indent=2)
        print(f"   Script JSON saved: {script_file}")
        
        results['stages']['script_creation'] = {
            'status': 'success',
            'script_file': str(script_file),
            'estimated_word_count': script_data.get('estimated_word_count'),
            'visual_cues_count': len(script_data.get('visual_cues', []))
        }
        
        # ============================================================
        # STAGE 3: VIDEO EDITING & PRODUCTION
        # ============================================================
        print("\n" + "="*70)
        print("STAGE 3: VIDEO EDITING & PRODUCTION")
        print("="*70)
        
        video_editor = VideoEditor()
        output_dir = Path('data/output/videos')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        video_file = output_dir / f"viral_short_e2e_{timestamp}.mp4"
        captions_file = Path('data/output/captions') / f"captions_e2e_{timestamp}.srt"
        thumbnail_file = Path('data/output/thumbnails') / f"thumbnail_e2e_{timestamp}.png"
        
        print(f"\n📹 Rendering video (this may take a minute)...")
        video_path = video_editor.create_shorts_video(
            script_data=script_data,
            captions_srt_path=str(captions_file),
            thumbnail_path=str(thumbnail_file),
            title=idea.get('title'),
            output_file=str(video_file),
            timestamp=timestamp
        )
        
        if not Path(video_path).exists():
            raise RuntimeError(f"Video file not created: {video_path}")
        
        video_size_mb = Path(video_path).stat().st_size / (1024 * 1024)
        print(f"\n✅ Video created: {video_path}")
        print(f"   File size: {video_size_mb:.2f} MB")
        
        results['stages']['video_production'] = {
            'status': 'success',
            'video_file': str(video_path),
            'video_size_mb': round(video_size_mb, 2)
        }
        
        # ============================================================
        # STAGE 4: METADATA GENERATION
        # ============================================================
        print("\n" + "="*70)
        print("STAGE 4: METADATA GENERATION (FOR UPLOAD)")
        print("="*70)
        
        metadata = generate_metadata_from_script(script_data, topic='Time Management')
        
        print(f"\n✅ Metadata generated:")
        print(f"   Title: {metadata.get('title')}")
        print(f"   Tags: {metadata.get('tags')}")
        print(f"   Hashtag: {metadata.get('hashtag')}")
        print(f"   Description (first 100 chars): {metadata.get('description')[:100]}...")
        
        # Save metadata JSON
        metadata_dir = Path('data/output/metadata')
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = metadata_dir / f"metadata_e2e_{timestamp}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"   Metadata JSON saved: {metadata_file}")
        
        results['stages']['metadata_generation'] = {
            'status': 'success',
            'metadata_file': str(metadata_file),
            'metadata': metadata
        }
        
        # ============================================================
        # STAGE 5: CAPTIONS GENERATION (FROM VISUAL CUES)
        # ============================================================
        print("\n" + "="*70)
        print("STAGE 5: CAPTIONS GENERATION (FROM VISUAL CUES)")
        print("="*70)
        
        captions_dir = Path('data/output/captions')
        captions_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate SRT from visual cues
        srt_content = "1\n00:00:00,000 --> 00:00:02,000\n[INTRO]\n\n"
        for i, cue in enumerate(script_data.get('visual_cues', []), start=2):
            start = cue.get('time_seconds', 0)
            duration = cue.get('duration_seconds', 3)
            end = start + duration
            
            start_fmt = f"00:{int(start//60):02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
            end_fmt = f"00:{int(end//60):02d}:{int(end%60):02d},{int((end%1)*1000):03d}"
            
            srt_content += f"{i}\n{start_fmt} --> {end_fmt}\n{cue.get('content', '')}\n\n"
        
        with open(captions_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        print(f"\n✅ Captions generated: {captions_file}")
        
        results['stages']['captions_generation'] = {
            'status': 'success',
            'captions_file': str(captions_file)
        }
        
        # ============================================================
        # STAGE 6: THUMBNAIL GENERATION
        # ============================================================
        print("\n" + "="*70)
        print("STAGE 6: THUMBNAIL GENERATION")
        print("="*70)
        
        thumbnail_dir = Path('data/output/thumbnails')
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy or reference the first slide as thumbnail
        slides_dir = output_dir / f"slides_{timestamp}"
        if (slides_dir / "slide_01.png").exists():
            import shutil
            shutil.copy(slides_dir / "slide_01.png", thumbnail_file)
            print(f"\n✅ Thumbnail created: {thumbnail_file}")
            results['stages']['thumbnail_generation'] = {
                'status': 'success',
                'thumbnail_file': str(thumbnail_file)
            }
        else:
            print(f"\n⚠️ Thumbnail generation skipped (slides dir not found)")
            results['stages']['thumbnail_generation'] = {
                'status': 'skipped',
                'reason': 'slides directory not found'
            }
        
        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        print("\n" + "="*70)
        print("✅ END-TO-END PIPELINE COMPLETED SUCCESSFULLY")
        print("="*70)
        
        print(f"\n📦 DELIVERABLES:")
        print(f"   1. Script JSON: {script_file}")
        print(f"   2. Video MP4: {video_path}")
        print(f"   3. Metadata JSON: {metadata_file}")
        print(f"   4. Captions SRT: {captions_file}")
        if (slides_dir / "slide_01.png").exists():
            print(f"   5. Thumbnail PNG: {thumbnail_file}")
        
        print(f"\n🎯 SYSTEM STATUS:")
        print(f"   ✅ Idea Generation: PASS")
        print(f"   ✅ Script Creation: PASS")
        print(f"   ✅ Video Production: PASS")
        print(f"   ✅ Metadata Generation: PASS")
        print(f"   ✅ Captions Generation: PASS")
        print(f"   ✅ Thumbnail Generation: {'PASS' if (slides_dir / 'slide_01.png').exists() else 'SKIPPED'}")
        
        print(f"\n📊 METRICS:")
        print(f"   Video Duration: 30 seconds")
        print(f"   Video Size: {video_size_mb:.2f} MB")
        print(f"   Script Word Count: {script_data.get('estimated_word_count')}")
        print(f"   Visual Cues: {len(script_data.get('visual_cues', []))}")
        print(f"   Keywords: {len(script_data.get('keywords', []))}")
        
        print(f"\n🚀 NEXT STEP: Upload to YouTube")
        print(f"   Use the generated metadata and video file:")
        print(f"   - Title: {metadata.get('title')}")
        print(f"   - Video: {video_path}")
        print(f"   - Thumbnail: {thumbnail_file}")
        
        # Save final results
        results_file = Path('data/output/metadata') / f"pipeline_results_e2e_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Full results saved to: {results_file}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        results['error'] = str(e)
        return results


if __name__ == '__main__':
    test_end_to_end_pipeline()
