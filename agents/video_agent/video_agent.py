import os
import sys
from datetime import datetime
from pathlib import Path
# gTTS replaced with OpenAI TTS
from mutagen.mp3 import MP3
from video_gen import create_video_with_word_captions, create_multi_story_video, detect_smart_story_boundaries
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directories to path to import from other agents
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'news_agent'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from generate_summary import generate_news_script
from video_database import initialize_database, insert_video_record, get_db_path

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def create_voiceover(script, output_dir="voiceovers"):
    # Create output directory if it doesn't exist (relative to script location)
    # Get the directory where this script is located (agents/video_agent/)
    script_dir = Path(__file__).parent.resolve()
    
    # Create the output directory path (agents/video_agent/voiceovers/)
    output_path = script_dir / output_dir
    output_path = output_path.resolve()  # Ensure absolute path
    
    # Create the directory if it doesn't exist (with parents if needed)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_path}")
    
    # Generate timestamp for filenames (format: YYYYMMDD_HHMMSS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Define file paths with timestamps - ALWAYS use output_path
    script_filename = f"script_{timestamp}.txt"
    audio_filename = f"voiceover_{timestamp}.mp3"
    
    # Build file paths using the resolved output_path to ensure files go in voiceovers/
    script_path = output_path / script_filename
    audio_path = output_path / audio_filename
    
    # Ensure paths are absolute and resolve any symlinks
    script_path = script_path.resolve()
    audio_path = audio_path.resolve()
    
    # Verify paths are in the correct directory before saving (use path comparison)
    try:
        script_path.relative_to(output_path)
        audio_path.relative_to(output_path)
    except ValueError as e:
        raise ValueError(
            f"Path validation failed. Script: {script_path}, Audio: {audio_path}, "
            f"Output dir: {output_path}. Error: {e}"
        )
    
    # Save the script to a text file
    print(f"Saving script to {script_path}...")
    print(script)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    
    # Generate and save the voiceover using OpenAI TTS
    print(f"Generating voiceover audio with OpenAI TTS...")
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.audio.speech.create(
        model="tts-1",  # Use "tts-1-hd" for higher quality
        voice="nova",   # Options: alloy, echo, fable, onyx, nova, shimmer
        input=script
    )
    response.stream_to_file(str(audio_path))
    print(f"Voiceover saved to {audio_path}")
    
    # Calculate audio duration
    duration = None
    try:
        audio_file = MP3(str(audio_path))
        duration = audio_file.info.length  # Duration in seconds
    except Exception as e:
        print(f"Warning: Could not determine audio duration: {e}")
    
    return {
        'script_path': str(script_path),
        'audio_path': str(audio_path),
        'timestamp': timestamp,
        'duration': duration
    }




# Allow running as a standalone script
if __name__ == "__main__":
    story_count = 4
    result = create_voiceover(story_count=story_count)
    print(f"\nVoiceover generation complete!")
    print(f"Script: {result['script_path']}")
    print(f"Audio: {result['audio_path']}")

    # Setup paths
    script_dir = Path(__file__).parent.resolve()
    thumbnails_dir = script_dir / "thumbnails"
    thumbnails_dir.mkdir(exist_ok=True)
    timestamp = result['timestamp']
    output_video_path = script_dir / "Story.mp4"
    
    # Get script and metadata
    script_text = result.get('script', '')
    story_metadata = result.get('story_metadata', {})
    
    # For multi-story videos, generate multiple thumbnails
    if story_count > 1:
        print(f"\n=== Creating Multi-Story Video with {story_count} segments ===")
        
        # Detect story boundaries FIRST to get actual text per story
        print("\nDetecting story boundaries and extracting text...")
        story_segments = detect_smart_story_boundaries(result['audio_path'], story_count)
        
        if not story_segments:
            print("❌ Failed to detect story boundaries. Aborting.")
        else:
            # Generate thumbnails based on ACTUAL story text
            thumbnail_paths = []
            for i, segment in enumerate(story_segments):
                print(f"\nGenerating thumbnail {i+1}/{story_count} based on story content...")
                thumb_path = thumbnails_dir / f"thumbnail_{timestamp}_story{i+1}.png"
                
                # Use first 150 characters of actual story text for better image generation
                story_preview = segment['text'][:150]
                prompt = f"Create a professional news thumbnail image for this story: {story_preview}. Style: modern news broadcast, clean, professional, high quality. Do not include any text in the image."
                
                try:
                    client = OpenAI(api_key=OPENAI_API_KEY)
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        n=1,
                        size="1024x1024"
                    )
                    image_url = response.data[0].url
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    with open(thumb_path, "wb") as f:
                        f.write(img_response.content)
                    print(f"✅ Thumbnail {i+1} saved: {thumb_path}")
                    print(f"   Based on: {story_preview}...")
                    thumbnail_paths.append(str(thumb_path))
                except Exception as e:
                    print(f"⚠️  Failed to generate thumbnail {i+1}: {e}")
                    if thumbnail_paths:
                        thumbnail_paths.append(thumbnail_paths[-1])
                    else:
                        print("❌ Failed to generate any thumbnails. Aborting.")
                        exit(1)
            
            # Extract boundaries from segments
            boundaries = [(seg['start'], seg['end']) for seg in story_segments]
            
            if len(thumbnail_paths) == story_count:
                print(f"\n🎬 Creating multi-story video with dynamic effects...")
                print(f"Audio: {result['audio_path']}")
                print(f"Thumbnails: {len(thumbnail_paths)}")
                print(f"Boundaries: {boundaries}")
                
                success = create_multi_story_video(
                    audio_file=result['audio_path'],
                    image_files=thumbnail_paths,
                    story_boundaries=boundaries,
                    output_file=str(output_video_path)
                )
                
                if success:
                    print(f"\n✅ Multi-story video created successfully: {output_video_path}")
                else:
                    print(f"\n❌ Failed to create multi-story video")
            else:
                print("❌ Error: Could not create video - missing thumbnails")
    
    else:
        # Single story video (original behavior)
        print(f"\n=== Creating Single Story Video ===")
        thumbnail_path = thumbnails_dir / f"thumbnail_{timestamp}.png"
        headline = story_metadata.get('headline') if story_metadata else None
        
        # Generate thumbnail
        try:
            prompt = f"Create a professional news thumbnail image for this headline: {headline}. Style: modern news broadcast, clean, professional, high quality. Do not include any text in the image." if headline else f"Create a professional news thumbnail image for this story: {script_text[:150]}. Style: modern news broadcast, clean, professional, high quality. Do not include any text in the image."
            
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            image_url = response.data[0].url
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            with open(thumbnail_path, "wb") as f:
                f.write(img_response.content)
            print(f"✅ Thumbnail saved: {thumbnail_path}")
            
            print("\nGenerating video with word captions...")
            print(f"Using audio from: {result['audio_path']}")
            print(f"Using thumbnail from: {thumbnail_path}")
            create_video_with_word_captions(
                audio_file=result['audio_path'],
                image_file=str(thumbnail_path),
                output_file=str(output_video_path)
            )
            print(f"✅ Video created: {output_video_path}")
        except Exception as e:
            print(f"❌ Failed to generate thumbnail: {e}")
