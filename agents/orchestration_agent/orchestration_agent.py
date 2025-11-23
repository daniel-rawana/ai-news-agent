import os
import sys
from pathlib import Path
from datetime import datetime
from typing import TypedDict, List, Optional, Annotated
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import requests
from openai import OpenAI
from mutagen.mp3 import MP3
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'news_agent'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'video_agent'))

from fetch_news import fetch_news
from generate_summary import generate_news_script
from video_gen import create_video_with_word_captions, create_multi_story_video, detect_smart_story_boundaries
from video_database import initialize_database, insert_video_record, get_db_path, update_video_status

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class NewsVideoState(TypedDict):
    """State passed between all nodes in the workflow."""
    story_count: int                    # Number of stories to process
    stories: List[dict]                 # Fetched news stories
    script: str                         # Generated news script
    script_data: dict                   # Full script data with metadata
    audio_path: str                     # Path to voiceover MP3
    script_path: str                    # Path to saved script
    timestamp: str                      # Timestamp for file naming
    thumbnails: List[str]               # Paths to generated thumbnails
    story_boundaries: List[tuple]       # (start, end) tuples for each story
    story_segments: List[dict]          # Full segment data with text
    video_path: str                     # Path to final video
    video_id: Optional[int]             # Database record ID
    duration: Optional[float]           # Audio duration in seconds
    error: Optional[str]                # Error message if any
    status: str                         # Current pipeline status

def fetch_news_node(state: NewsVideoState) -> dict:
    try:
        stories = fetch_news(count=3)

        return {
            "stories": stories,
            "status": "news_fetched"
        }
    
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def generate_script_node(state: NewsVideoState) -> dict:
    if state.get("error"):
        return {}

    try:
        story_count = state.get("story_count", 3)
        result = generate_news_script(story_count, return_metadata=True)

        if isinstance(result, dict):
            script_data = result.get('script', {})
            if isinstance(script_data, dict):
                script = script_data.get('summary', '')
            else:
                script = str(script_data)
            story_metadata = result.get('story_metadata')
        else:
            script = result
            script_data = {}
            story_metadata = None

        print(f" Script generated ({len(script)} chars)")
        return {
            "script": script,
            "script_data": script_data,
            "story_metadata": story_metadata,
            "status": "script_generated"
        }
    except Exception as e:
        print(f"L Error generating script: {e}")
        return {"error": str(e), "status": "failed"}


def create_voiceover_node(state: NewsVideoState) -> dict:
    """Create voiceover audio using OpenAI TTS."""
    print("\n<� [Node] Creating voiceover...")

    if state.get("error"):
        return {}

    try:
        script = state["script"]

        # Setup paths
        script_dir = Path(__file__).parent.parent / "video_agent"
        output_path = script_dir / "voiceovers"
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_path = output_path / f"script_{timestamp}.txt"
        audio_path = output_path / f"voiceover_{timestamp}.mp3"

        # Save script
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)

        # Generate voiceover with OpenAI TTS
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=script
        )
        response.stream_to_file(str(audio_path))

        # Get duration
        duration = None
        try:
            audio_file = MP3(str(audio_path))
            duration = audio_file.info.length
        except Exception as e:
            print(f"Warning: Could not determine duration: {e}")

        print(f" Voiceover saved: {audio_path}")
        return {
            "audio_path": str(audio_path),
            "script_path": str(script_path),
            "timestamp": timestamp,
            "duration": duration,
            "status": "voiceover_created"
        }
    except Exception as e:
        print(f"L Error creating voiceover: {e}")
        return {"error": str(e), "status": "failed"}


def save_initial_record_node(state: NewsVideoState) -> dict:
    """Save initial database record with processing status."""
    print("\n=� [Node] Saving initial database record...")

    if state.get("error"):
        return {}

    try:
        story_metadata = state.get("story_metadata", {})

        video_id = insert_video_record(
            timestamp=state["timestamp"],
            script_path=state["script_path"],
            audio_path=state["audio_path"],
            video_path=None,
            headline=story_metadata.get('headline') if story_metadata else None,
            summary=story_metadata.get('summary') if story_metadata else None,
            source=story_metadata.get('source') if story_metadata else None,
            duration=state.get("duration"),
            status="processing"
        )

        print(f" Database record created: ID {video_id}")
        return {
            "video_id": video_id,
            "status": "record_saved"
        }
    except Exception as e:
        print(f"L Error saving to database: {e}")
        return {"error": str(e), "status": "failed"}


def detect_boundaries_node(state: NewsVideoState) -> dict:
    """Detect story boundaries using Whisper transcription."""
    print("\n=
 [Node] Detecting story boundaries...")

    if state.get("error"):
        return {}

    try:
        story_count = state.get("story_count", 3)
        story_segments = detect_smart_story_boundaries(
            state["audio_path"],
            story_count
        )

        if not story_segments:
            raise Exception("Failed to detect story boundaries")

        boundaries = [(seg['start'], seg['end']) for seg in story_segments]

        print(f" Detected {len(boundaries)} story segments")
        return {
            "story_boundaries": boundaries,
            "story_segments": story_segments,
            "status": "boundaries_detected"
        }
    except Exception as e:
        print(f"L Error detecting boundaries: {e}")
        return {"error": str(e), "status": "failed"}


def generate_thumbnails_node(state: NewsVideoState) -> dict:
    """Generate thumbnails for each story using DALL-E 3."""
    print("\n=� [Node] Generating thumbnails...")

    if state.get("error"):
        return {}

    try:
        script_dir = Path(__file__).parent.parent / "video_agent"
        thumbnails_dir = script_dir / "thumbnails"
        thumbnails_dir.mkdir(exist_ok=True)

        timestamp = state["timestamp"]
        story_segments = state.get("story_segments", [])
        story_count = state.get("story_count", 3)

        client = OpenAI(api_key=OPENAI_API_KEY)
        thumbnail_paths = []

        for i, segment in enumerate(story_segments):
            print(f"  Generating thumbnail {i+1}/{story_count}...")
            thumb_path = thumbnails_dir / f"thumbnail_{timestamp}_story{i+1}.png"

            # Use story text for better image generation
            story_preview = segment.get('text', '')[:150]
            prompt = f"Create a professional news thumbnail image for this story: {story_preview}. Style: modern news broadcast, clean, professional, high quality. Do not include any text in the image."

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

            thumbnail_paths.append(str(thumb_path))
            print(f"   Thumbnail {i+1} saved")

        print(f" Generated {len(thumbnail_paths)} thumbnails")
        return {
            "thumbnails": thumbnail_paths,
            "status": "thumbnails_generated"
        }
    except Exception as e:
        print(f"L Error generating thumbnails: {e}")
        return {"error": str(e), "status": "failed"}


def create_video_node(state: NewsVideoState) -> dict:
    """Create the final video with FFmpeg."""
    print("\n<� [Node] Creating video...")

    if state.get("error"):
        return {}

    try:
        script_dir = Path(__file__).parent.parent / "video_agent"
        output_video_path = script_dir / "Story.mp4"

        story_count = state.get("story_count", 3)

        if story_count > 1:
            # Multi-story video
            success = create_multi_story_video(
                audio_file=state["audio_path"],
                image_files=state["thumbnails"],
                story_boundaries=state["story_boundaries"],
                output_file=str(output_video_path)
            )
        else:
            # Single story video
            create_video_with_word_captions(
                audio_file=state["audio_path"],
                image_file=state["thumbnails"][0],
                output_file=str(output_video_path)
            )
            success = True

        if not success:
            raise Exception("Video creation failed")

        print(f" Video created: {output_video_path}")
        return {
            "video_path": str(output_video_path),
            "status": "video_created"
        }
    except Exception as e:
        print(f"L Error creating video: {e}")
        return {"error": str(e), "status": "failed"}


def finalize_record_node(state: NewsVideoState) -> dict:
    """Update database record with final video path and completed status."""
    print("\n [Node] Finalizing database record...")

    if state.get("error"):
        # Mark as failed if there was an error
        if state.get("video_id"):
            try:
                update_video_status(state["video_id"], "failed")
            except:
                pass
        return {"status": "failed"}

    try:
        if state.get("video_id"):
            update_video_status(
                state["video_id"],
                "completed",
                video_path=state.get("video_path")
            )

        print(f" Pipeline completed successfully!")
        return {"status": "completed"}
    except Exception as e:
        print(f"L Error finalizing record: {e}")
        return {"error": str(e), "status": "failed"}

def create_news_video_graph():
    """
    Create and compile the LangGraph workflow for news video generation.

    Returns:
        CompiledGraph: The compiled workflow graph
    """
    workflow = StateGraph(NewsVideoState)

    # Add all nodes
    workflow.add_node("fetch_news", fetch_news_node)
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("create_voiceover", create_voiceover_node)
    workflow.add_node("save_initial_record", save_initial_record_node)
    workflow.add_node("detect_boundaries", detect_boundaries_node)
    workflow.add_node("generate_thumbnails", generate_thumbnails_node)
    workflow.add_node("create_video", create_video_node)
    workflow.add_node("finalize_record", finalize_record_node)

    # Define deterministic edges (sequential flow)
    workflow.set_entry_point("fetch_news")
    workflow.add_edge("fetch_news", "generate_script")
    workflow.add_edge("generate_script", "create_voiceover")
    workflow.add_edge("create_voiceover", "save_initial_record")
    workflow.add_edge("save_initial_record", "detect_boundaries")
    workflow.add_edge("detect_boundaries", "generate_thumbnails")
    workflow.add_edge("generate_thumbnails", "create_video")
    workflow.add_edge("create_video", "finalize_record")
    workflow.add_edge("finalize_record", END)

    return workflow.compile()


def create_news_video_graph_with_checkpointing(db_path: str = "checkpoints.db"):
    """
    Create the workflow with SQLite checkpointing for resumability.

    Args:
        db_path: Path to SQLite database for checkpoints

    Returns:
        CompiledGraph: The compiled workflow with checkpointing
    """
    workflow = StateGraph(NewsVideoState)

    # Add all nodes
    workflow.add_node("fetch_news", fetch_news_node)
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("create_voiceover", create_voiceover_node)
    workflow.add_node("save_initial_record", save_initial_record_node)
    workflow.add_node("detect_boundaries", detect_boundaries_node)
    workflow.add_node("generate_thumbnails", generate_thumbnails_node)
    workflow.add_node("create_video", create_video_node)
    workflow.add_node("finalize_record", finalize_record_node)

    # Define deterministic edges
    workflow.set_entry_point("fetch_news")
    workflow.add_edge("fetch_news", "generate_script")
    workflow.add_edge("generate_script", "create_voiceover")
    workflow.add_edge("create_voiceover", "save_initial_record")
    workflow.add_edge("save_initial_record", "detect_boundaries")
    workflow.add_edge("detect_boundaries", "generate_thumbnails")
    workflow.add_edge("generate_thumbnails", "create_video")
    workflow.add_edge("create_video", "finalize_record")
    workflow.add_edge("finalize_record", END)

    # Add checkpointing
    memory = SqliteSaver.from_conn_string(db_path)
    return workflow.compile(checkpointer=memory)

def run_news_video_pipeline(story_count: int = 4):
    """
    Run the complete news video generation pipeline.

    Args:
        story_count: Number of news stories to include

    Returns:
        dict: Final state with video_path and status
    """
    print("=" * 60)
    print("=� HERMES AI News Video Pipeline")
    print("=" * 60)

    # Initialize database
    initialize_database()

    # Create and run the graph
    graph = create_news_video_graph()

    # Initial state
    initial_state = {
        "story_count": story_count,
        "stories": [],
        "script": "",
        "script_data": {},
        "audio_path": "",
        "script_path": "",
        "timestamp": "",
        "thumbnails": [],
        "story_boundaries": [],
        "story_segments": [],
        "video_path": "",
        "video_id": None,
        "duration": None,
        "error": None,
        "status": "starting"
    }

    # Execute the workflow
    result = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    if result.get("error"):
        print(f"L Pipeline failed: {result['error']}")
    else:
        print(f" Pipeline completed successfully!")
        print(f"=� Video: {result.get('video_path')}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    result = run_news_video_pipeline(story_count=4)