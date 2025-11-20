"""
This script is used to generate a video from a story.
"""


import whisper
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
import os
from pathlib import Path
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# Effect styles for different video segments
EFFECT_STYLES = {
    'zoom_in': {
        'z': "min(zoom+0.0004,1.25)",
        'x': "iw/2-(iw/zoom/2)",
        'y': "ih/2-(ih/zoom/2)",
        'description': 'Zoom in 25%'
    },
    'zoom_out': {
        'z': "if(lte(zoom,1.01),1.25,max(zoom-0.0004,1.0))",
        'x': "iw/2-(iw/zoom/2)",
        'y': "ih/2-(ih/zoom/2)",
        'description': 'Zoom out from 25%'
    },
    'pan_right': {
        'z': "min(zoom+0.0002,1.15)",
        'x': "iw/2-(iw/zoom/2)+on*2",
        'y': "ih/2-(ih/zoom/2)",
        'description': 'Pan right with slight zoom'
    },
    'pan_left': {
        'z': "min(zoom+0.0002,1.15)",
        'x': "iw/2-(iw/zoom/2)-on*2",
        'y': "ih/2-(ih/zoom/2)",
        'description': 'Pan left with slight zoom'
    },
    'ken_burns': {
        'z': "min(zoom+0.0003,1.20)",
        'x': "iw/2-(iw/zoom/2)+on*1.5",
        'y': "ih/2-(ih/zoom/2)+on*1",
        'description': 'Ken Burns effect - zoom + pan'
    }
}


def get_word_timestamps_free(audio_file):
    """Get word-level timestamps using FREE local Whisper"""
    print("Loading Whisper model (this may take a moment on first run)...")
    model = whisper.load_model("base")
    
    print(f"Transcribing {audio_file}...")
    result = model.transcribe(audio_file, word_timestamps=True)
    
    text_segments = []
    for segment in result['segments']:
        if 'words' in segment:
            for word in segment['words']:
                text_segments.append((
                    word['start'],
                    word['end'],
                    word['word'].strip()
                ))
    
    print(f"Found {len(text_segments)} words with timestamps")
    return text_segments

def format_ass_time(seconds):
    """Convert seconds to ASS time format H:MM:SS.CS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def detect_smart_story_boundaries(audio_file, story_count):
    """
    Intelligently detect story boundaries by transcribing audio and dividing text.
    Ensures boundaries are continuous with no gaps.
    
    Args:
        audio_file: Path to audio file
        story_count: Number of stories to detect
    
    Returns:
        List of dicts with 'start', 'end', 'text' for each story segment
    """
    print(f"Detecting {story_count} story boundaries intelligently...")
    
    # Load Whisper model and transcribe
    print("Loading Whisper model for boundary detection...")
    model = whisper.load_model("base")
    
    print(f"Transcribing {audio_file} for text extraction...")
    result = model.transcribe(audio_file, word_timestamps=True)
    
    # Extract all words with timestamps
    word_data = []
    for segment in result['segments']:
        if 'words' in segment:
            for word in segment['words']:
                word_data.append({
                    'start': word['start'],
                    'end': word['end'],
                    'text': word['word'].strip()
                })
    
    if not word_data:
        print("Warning: No words found in transcription")
        return None
    
    total_words = len(word_data)
    print(f"Transcribed {total_words} words")
    
    # Get actual audio duration from file (not just last word timestamp)
    audio_info = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_file
    ], capture_output=True, text=True, check=True)
    total_duration = float(audio_info.stdout.strip())
    print(f"Audio duration: {total_duration:.2f}s (last word ends at {word_data[-1]['end']:.2f}s)")
    
    # Try to detect natural story boundaries using transition markers
    transition_markers = ['Meanwhile', 'Finally', 'In other news', 'Additionally', 'Also', 'Furthermore']
    boundary_indices = [0]  # Always start at word 0
    
    # Find words that match transition markers
    for i, word in enumerate(word_data):
        word_clean = word['text'].lower().strip('.,!?')
        for marker in transition_markers:
            if word_clean == marker.lower():
                if i > 0 and i not in boundary_indices:
                    boundary_indices.append(i)
                    print(f"Found transition marker '{word['text']}' at word {i}")
                    break
    
    boundary_indices.append(total_words)
    boundary_indices = sorted(set(boundary_indices))
    
    # If we found the right number of natural boundaries, use them; otherwise fall back
    if len(boundary_indices) - 1 == story_count:
        print(f"✓ Using {len(boundary_indices) - 1} natural story boundaries")
    else:
        print(f"Found {len(boundary_indices) - 1} natural boundaries, need {story_count}. Using equal division.")
        words_per_story = total_words // story_count
        boundary_indices = [i * words_per_story for i in range(story_count)] + [total_words]
    
    # Create segments from boundaries
    story_segments = []
    for i in range(len(boundary_indices) - 1):
        start_word_idx = boundary_indices[i]
        end_word_idx = boundary_indices[i + 1]
        segment_words = word_data[start_word_idx:end_word_idx]
        
        if segment_words:
            # Start time: first word or previous segment's end for continuity
            if i == 0:
                start_time = segment_words[0]['start']
            else:
                start_time = story_segments[-1]['end']
            
            # End time: last segment uses total audio duration
            if i == len(boundary_indices) - 2:
                end_time = total_duration
            else:
                end_time = segment_words[-1]['end']
            
            text = ' '.join([w['text'] for w in segment_words])
            
            story_segments.append({
                'start': start_time,
                'end': end_time,
                'text': text
            })
            
            print(f"Story {i+1}: {start_time:.1f}s - {end_time:.1f}s ({len(segment_words)} words)")
            print(f"  Preview: {text[:80]}...")
    
    return story_segments


def create_video_segment_videoonly(image_file, duration, effect_style, output_file):
    """
    Create a video segment (video only, no audio) with a specific effect.
    
    Args:
        image_file: Path to image
        duration: Duration in seconds
        effect_style: Effect to apply
        output_file: Output video path
    
    Returns:
        bool: True if successful
    """
    effect = EFFECT_STYLES.get(effect_style, EFFECT_STYLES['zoom_in'])
    fps = 25
    d_value = int(duration * fps)
    
    try:
        command = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', image_file,
            '-filter_complex', (
                f"[0:v]scale=4096x4096,"
                f"zoompan=z='{effect['z']}':x='{effect['x']}':y='{effect['y']}':d={d_value}:s=4096x4096:fps={fps},"
                f"scale=1024x1024[v]"
            ),
            '-map', '[v]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-t', str(duration),
            '-pix_fmt', 'yuv420p',
            '-an',  # No audio
            output_file
        ]
        
        subprocess.run(command, check=True, capture_output=True, text=True)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating video segment: {e}")
        if e.stderr:
            print(f"FFmpeg stderr: {e.stderr[-500:]}")
        return False


def create_multi_story_video(audio_file, image_files, story_boundaries, output_file):
    """
    Create a video with multiple images (one per story) with different effects.
    Uses a single continuous audio track to avoid cuts.
    
    Args:
        audio_file: Path to combined audio file
        image_files: List of image paths (one per story)
        story_boundaries: List of (start, end) tuples for each story
        output_file: Output video path
    
    Returns:
        bool: True if successful
    """
    if len(image_files) != len(story_boundaries):
        print("Error: Number of images must match number of story boundaries")
        return False
    
    # Effect rotation for visual variety
    effects = ['zoom_in', 'pan_right', 'zoom_out', 'ken_burns']
    
    print("Creating video with continuous audio and dynamic visuals...")
    
    # Step 1: Create video-only segments (no audio)
    video_segments = []
    for i, (image, (start, end)) in enumerate(zip(image_files, story_boundaries)):
        effect = effects[i % len(effects)]
        duration = end - start
        segment_file = f"temp_vseg_{i}.mp4"
        
        print(f"Creating visual segment {i+1}/{len(image_files)} with {effect}...")
        success = create_video_segment_videoonly(
            image_file=image,
            duration=duration,
            effect_style=effect,
            output_file=segment_file
        )
        
        if success:
            video_segments.append(segment_file)
        else:
            print(f"Failed to create segment {i}")
            # Clean up
            for seg in video_segments:
                if os.path.exists(seg):
                    os.remove(seg)
            return False
    
    # Step 2: Concatenate video segments
    concat_file = "concat_list.txt"
    with open(concat_file, 'w') as f:
        for seg in video_segments:
            f.write(f"file '{seg}'\n")
    
    try:
        # Concat videos
        print("Concatenating video segments...")
        subprocess.run([
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            'temp_video_only.mp4'
        ], check=True, capture_output=True, text=True)
        
        # Step 3: Add continuous audio track
        print("Adding continuous audio track...")
        
        # Get audio duration first to ensure video matches
        audio_info = subprocess.run([
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ], capture_output=True, text=True, check=True)
        audio_duration = float(audio_info.stdout.strip())
        print(f"Audio duration: {audio_duration:.2f}s")
        
        subprocess.run([
            'ffmpeg', '-y',
            '-i', 'temp_video_only.mp4',
            '-i', audio_file,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-t', str(audio_duration),
            'temp_video_with_audio.mp4'
        ], check=True, capture_output=True, text=True)
        
        # Step 4: Add captions
        print("Adding word-level captions...")
        success = add_captions_to_video(audio_file, 'temp_video_with_audio.mp4', output_file)
        
        # Clean up
        os.remove(concat_file)
        for seg in video_segments:
            if os.path.exists(seg):
                os.remove(seg)
        if os.path.exists('temp_video_only.mp4'):
            os.remove('temp_video_only.mp4')
        if os.path.exists('temp_video_with_audio.mp4'):
            os.remove('temp_video_with_audio.mp4')
        
        return success
        
    except subprocess.CalledProcessError as e:
        print(f"Error creating multi-story video: {e}")
        if e.stderr:
            print(f"FFmpeg stderr: {e.stderr[-500:]}")
        # Clean up
        if os.path.exists(concat_file):
            os.remove(concat_file)
        for seg in video_segments:
            if os.path.exists(seg):
                os.remove(seg)
        if os.path.exists('temp_video_only.mp4'):
            os.remove('temp_video_only.mp4')
        if os.path.exists('temp_video_with_audio.mp4'):
            os.remove('temp_video_with_audio.mp4')
        return False


def add_captions_to_video(audio_file, video_file, output_file):
    """
    Add word-level captions to an existing video.
    
    Args:
        audio_file: Path to audio (for transcription)
        video_file: Path to video to add captions to
        output_file: Output video path
    
    Returns:
        bool: True if successful
    """
    # Get timestamps from audio
    word_segments = get_word_timestamps_free(audio_file)
    
    # Group words into phrases (4 words each for better readability)
    phrase_segments = []
    words_per_phrase = 4
    
    for i in range(0, len(word_segments), words_per_phrase):
        phrase_words = word_segments[i:i+words_per_phrase]
        if phrase_words:
            start = phrase_words[0][0]
            end = phrase_words[-1][1]
            text = ' '.join([word[2] for word in phrase_words])
            phrase_segments.append((start, end, text))
    
    print(f"Created {len(phrase_segments)} phrase segments")
    
    # Create ASS subtitle file
    ass_file = "captions.ass"
    with open(ass_file, 'w', encoding='utf-8') as f:
        f.write("[Script Info]\n")
        f.write("ScriptType: v4.00+\n")
        f.write("PlayResX: 1024\n")
        f.write("PlayResY: 1024\n\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write("Style: Default,Arial,60,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,2,0,2,10,10,100,1\n\n")
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        
        for start, end, text in phrase_segments:
            start_time = format_ass_time(start)
            end_time = format_ass_time(end)
            f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
    
    try:
        command = [
            'ffmpeg', '-y',
            '-i', video_file,
            '-vf', f"ass={ass_file}",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-c:a', 'copy',
            '-pix_fmt', 'yuv420p',
            output_file
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        
        # Clean up
        os.remove(ass_file)
        
        print(f"Captions added successfully: {output_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error adding captions: {e}")
        if os.path.exists(ass_file):
            os.remove(ass_file)
        return False


def create_video_with_word_captions(audio_file, image_file, output_file):
    """Creates video with phrase-by-phrase captions using ASS subtitles"""
    
    # Get timestamps from audio
    word_segments = get_word_timestamps_free(audio_file)
    
    # Group words into phrases (3-5 words each for better readability)
    phrase_segments = []
    words_per_phrase = 4
    
    for i in range(0, len(word_segments), words_per_phrase):
        phrase_words = word_segments[i:i+words_per_phrase]
        if phrase_words:
            start = phrase_words[0][0]
            end = phrase_words[-1][1]
            text = ' '.join([word[2] for word in phrase_words])
            phrase_segments.append((start, end, text))
    
    print(f"Created {len(phrase_segments)} phrase segments from {len(word_segments)} words")
    
    # Create ASS subtitle file
    ass_file = "captions.ass"
    with open(ass_file, 'w', encoding='utf-8') as f:
        # Write ASS header
        f.write("[Script Info]\n")
        f.write("ScriptType: v4.00+\n")
        f.write("PlayResX: 1024\n")
        f.write("PlayResY: 1024\n")
        f.write("\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write("Style: Default,Arial,60,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,2,0,2,10,10,100,1\n")
        f.write("\n")
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        
        # Write subtitle events
        for start, end, text in phrase_segments:
            # Convert seconds to ASS time format (H:MM:SS.CS)
            start_time = format_ass_time(start)
            end_time = format_ass_time(end)
            # ASS format handles all special characters automatically
            f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
    
    try:
        # Add zoom effect with upscale/downscale to eliminate shakiness
        # NO -loop or -framerate: use large d value and let zoompan generate frames
        # d=750 creates 30 seconds of frames at 25fps, -shortest cuts to audio length
        # Method: Upscale 4x -> apply zoom -> downscale back to prevent rounding errors
        command = [
            'ffmpeg',
            '-i', image_file,  # Single image input, no looping
            '-i', audio_file,
            '-filter_complex', (
                "[0:v]scale=4096x4096,"  # Upscale 4x to prevent rounding errors
                "zoompan=z='min(zoom+0.0004,1.20)':d=750:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=4096x4096:fps=25,"
                "scale=1024x1024[v];"  # Downscale back to target resolution
                f"[v]ass={ass_file}[vout]"  # Apply subtitles
            ),
            '-map', '[vout]',  # Map filtered video
            '-map', '1:a',     # Map audio from second input
            '-c:v', 'libx264',
            '-preset', 'medium',  # Good balance of speed and quality
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            '-y',
            output_file
        ]
        
        print("Running ffmpeg command with smooth zoom and ASS subtitles...")
        print(f"Number of caption segments: {len(phrase_segments)}")
        print(f"Zoom effect: 1.0x to 1.20x (20%) - SMOOTH (upscale/downscale method)")
        print(f"Full command: {' '.join(command)}")
        print("\n--- FFmpeg Output ---")
        
        # Run ffmpeg with visible progress output
        result = subprocess.run(command, check=True, text=True)
        print("\n--- FFmpeg Complete ---")
        print(f"Video with phrase captions created: {output_file}")
        
        # Clean up the ASS file
        os.remove(ass_file)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False