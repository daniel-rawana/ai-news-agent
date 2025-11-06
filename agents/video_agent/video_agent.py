import os
import sys
from datetime import datetime
from pathlib import Path
from gtts import gTTS
from mutagen.mp3 import MP3

# Add parent directories to path to import from other agents
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'news_agent'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from generate_summary import generate_news_script
from video_database import initialize_database, insert_video_record, get_db_path


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
        script = result.get('script', '')
        script = script['summary']
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
        'video_id': video_id
    }


# Allow running as a standalone script
if __name__ == "__main__":
    result = create_voiceover()
    print(f"\nVoiceover generation complete!")
    print(f"Script: {result['script_path']}")
    print(f"Audio: {result['audio_path']}")
