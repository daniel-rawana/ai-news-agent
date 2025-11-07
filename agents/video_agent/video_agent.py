import os
import sys
from datetime import datetime
from pathlib import Path
from gtts import gTTS
from mutagen.mp3 import MP3
from video_gen import create_video_with_word_captions
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


def create_voiceover(story_count=1, output_dir="voiceovers"):
    """
    Fetches news, generates a summary script, and creates a voiceover audio file.
    
    This function:
    1. Calls generate_news_script to fetch and summarize news
    2. Converts the script to speech using gTTS
    3. Saves both script and audio files with timestamps
    4. Organizes outputs in a 'voiceovers' directory
    
    Args:
        story_count (int): Number of news stories to process. Default is 1.
        output_dir (str): Directory name for saving outputs. Default is "voiceovers".
    
    Returns:
        dict: A dictionary containing:
            - 'script_path': Path to the saved text file
            - 'audio_path': Path to the saved MP3 file
            - 'timestamp': The timestamp used for filenames
    """
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
    
    # Generate the news script with metadata
    print("Fetching news and generating script...")
    result = generate_news_script(story_count, return_metadata=True)
    
    # Extract script and metadata
    if isinstance(result, dict):
        script_data = result.get('script', {})
        # script_data is a dict with 'summary' field (from summarize_story JSON response)
        if isinstance(script_data, dict):
            script = script_data.get('summary', '')
        else:
            # Fallback: if script_data is already a string, use it directly
            script = str(script_data)
        story_metadata = result.get('story_metadata')
    else:
        # Fallback if old format (shouldn't happen, but for safety)
        script = result
        story_metadata = None
    
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
    
    # Generate and save the voiceover - use absolute path string
    print(f"Generating voiceover audio...")
    tts = gTTS(text=script, lang='en', slow=False)
    tts.save(str(audio_path))
    print(f"Voiceover saved to {audio_path}")
    
    # Calculate audio duration
    duration = None
    try:
        audio_file = MP3(str(audio_path))
        duration = audio_file.info.length  # Duration in seconds
    except Exception as e:
        print(f"Warning: Could not determine audio duration: {e}")
    
    # Extract metadata
    headline = story_metadata.get('headline') if story_metadata else None
    summary = story_metadata.get('summary') if story_metadata else None
    source = story_metadata.get('source') if story_metadata else None
    
    # Save to database
    video_id = None
    try:
        # Verify database path is correct (use project root)
        db_path = get_db_path()
        print(f"Saving metadata to database at: {db_path}")
        video_id = insert_video_record(
            timestamp=timestamp,
            script_path=str(script_path),
            audio_path=str(audio_path),
            video_path=None,
            headline=headline,
            summary=summary,
            source=source,
            duration=duration,
            status="processing"
        )
        print(f"Video record created in database with ID: {video_id}")
    except Exception as e:
        print(f"Warning: Failed to save to database: {e}")
    
    return {
        'script_path': str(script_path),
        'audio_path': str(audio_path),
        'timestamp': timestamp,
        'video_id': video_id,
        'story_metadata': story_metadata,
        'script': script
    }


def generate_thumbnail(script_text, headline=None, output_path=None):
    """
    Generate a thumbnail image using DALL-E based on the news story.
    
    Args:
        script_text: The news script/summary text
        headline: Optional headline for better image generation
        output_path: Path where to save the thumbnail
    
    Returns:
        str: Path to the generated thumbnail, or None if generation failed
    """
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not found. Cannot generate thumbnail.")
        return None
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Create a prompt for the thumbnail
        if headline:
            prompt = f"Create a professional news thumbnail image for this headline: {headline}. Style: modern news broadcast, clean, professional, high quality. Do not include any text in the image."
        else:
            # Use first sentence of script as prompt
            first_sentence = script_text.split('.')[0] if script_text else "News broadcast"
            prompt = f"Create a professional news thumbnail image for this story: {first_sentence}. Style: modern news broadcast, clean, professional, high quality. Do not include any text in the image."
        
        print("Generating thumbnail image with DALL-E...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        
        image_url = response.data[0].url
        print(f"Thumbnail generated: {image_url}")
        
        # Download the image
        if output_path:
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(img_response.content)
            print(f"Thumbnail saved to: {output_path}")
            return str(output_path)
        else:
            return image_url
            
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None


# Allow running as a standalone script
if __name__ == "__main__":
    result = create_voiceover()
    print(f"\nVoiceover generation complete!")
    print(f"Script: {result['script_path']}")
    print(f"Audio: {result['audio_path']}")

    # Generate video with word captions
    # Get absolute path to thumbnail.png in the same directory as this script
    script_dir = Path(__file__).parent.resolve()
    thumbnail_path = script_dir / "thumbnail.png"
    output_video_path = script_dir / "Story.mp4"
    
    # Generate thumbnail if it doesn't exist
    thumbnail_ready = True
    if not thumbnail_path.exists():
        print(f"\nThumbnail not found at {thumbnail_path}. Generating one...")
        story_metadata = result.get('story_metadata', {})
        script_text = result.get('script', '')
        headline = story_metadata.get('headline') if story_metadata else None
        
        generated_thumbnail = generate_thumbnail(
            script_text=script_text,
            headline=headline,
            output_path=str(thumbnail_path)
        )
        
        if not generated_thumbnail:
            print("Failed to generate thumbnail. Skipping video generation.")
            thumbnail_ready = False
    
    # Generate video with word captions using audio from voiceovers
    if thumbnail_ready:
        print("\nGenerating video with word captions...")
        print(f"Using audio from: {result['audio_path']}")
        create_video_with_word_captions(
            audio_file=result['audio_path'],
            image_file=str(thumbnail_path),
            output_file=str(output_video_path)
        )
        print(f"Video with word captions created: {output_video_path}")
