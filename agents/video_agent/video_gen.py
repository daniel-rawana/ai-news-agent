"""
This script is used to generate a video from a story.
"""


import whisper
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


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
        command = [
            'ffmpeg',
            '-loop', '1',
            '-i', image_file,
            '-i', audio_file,
            '-vf', f"ass={ass_file}",  # Use ASS subtitles instead of drawtext
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            '-y',
            output_file
        ]
        
        print("Running ffmpeg command with ASS subtitles...")
        print(f"Number of caption segments: {len(phrase_segments)}")
        
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Video with phrase captions created: {output_file}")
        
        # Clean up the ASS file
        os.remove(ass_file)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False