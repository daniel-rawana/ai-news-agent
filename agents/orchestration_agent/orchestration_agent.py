import os
import sys
from pathlib import Path
from datetime import datetime
from typing import TypedDict, List, Optional, Annotated
import operator

from langgraph.graph import StateGraph, END
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
from video_agent import create_voiceover
from database_utils import upload_video_to_storage, upload_thumbnail_to_storage, upload_video_metadata

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
    print("[DEBUG] fetch_news_node starting...")
    try:
        stories = fetch_news(count=3)

        print("[DEBUG] fetch_news_node completed")
        return {
            "stories": stories,
            "status": "news_fetched"
        }

    except Exception as e:
        print(f"[DEBUG] fetch_news_node failed: {e}")
        return {"error": str(e), "status": "failed"}


def generate_script_node(state: NewsVideoState) -> dict:
    print("[DEBUG] generate_script_node starting...")
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

        print("[DEBUG] generate_script_node completed")
        return {
            "script": script,
            "script_data": script_data,
            "story_metadata": story_metadata,
            "status": "script_generated"
        }
    except Exception as e:
        print(f"[DEBUG] generate_script_node failed: {e}")
        return {"error": str(e), "status": "failed"}


def create_voiceover_node(state: NewsVideoState) -> dict:
    print("[DEBUG] create_voiceover_node starting...")
    if state.get("error"):
        return {}

    try:
        script = state["script"]

        voiceover = create_voiceover(script)

        print("[DEBUG] create_voiceover_node completed")
        return {
            "audio_path": voiceover['audio_path'],
            "script_path": voiceover['script_path'],
            "timestamp": voiceover['timestamp'],
            "duration": voiceover['duration'],
            "status": "voiceover_created"
        }
    except Exception as e:
        print(f"[DEBUG] create_voiceover_node failed: {e}")
        return {"error": str(e), "status": "failed"}


def detect_boundaries_node(state: NewsVideoState) -> dict:
    print("[DEBUG] detect_boundaries_node starting...")
    if state.get("error"):
        return {}

    try:
        story_count = state.get("story_count", 3)
        print(f"[DEBUG] Calling detect_smart_story_boundaries with audio: {state['audio_path']}")
        story_segments = detect_smart_story_boundaries(
            state["audio_path"],
            story_count
        )

        if not story_segments:
            raise Exception("Failed to detect story boundaries")

        boundaries = [(seg['start'], seg['end']) for seg in story_segments]

        print(f"[DEBUG] detect_boundaries_node completed, found {len(boundaries)} boundaries")
        return {
            "story_boundaries": boundaries,
            "story_segments": story_segments,
            "status": "boundaries_detected"
        }
    except Exception as e:
        print(f"[DEBUG] detect_boundaries_node failed: {e}")
        return {"error": str(e), "status": "failed"}


def generate_thumbnails_node(state: NewsVideoState) -> dict:
    print("[DEBUG] generate_thumbnails_node starting...")
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
            thumb_path = thumbnails_dir / f"thumbnail_{timestamp}_story{i+1}.png"

            # Use story text for better image generation
            story_preview = segment.get('text', '')[:150]
            prompt = f"Create a professional news thumbnail image for this story: {story_preview}. Style: modern news broadcast, clean, professional, high quality. Do not include any text in the image."

            # Try generating with the story prompt, fallback to generic if content policy violation
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    n=1,
                    size="1024x1024"
                )
            except Exception as dalle_error:
                error_str = str(dalle_error)
                if "content_policy_violation" in error_str or "safety system" in error_str:
                    print(f"[DEBUG] Content policy violation for thumbnail {i+1}, using generic prompt")
                    # Retry with ultra-safe generic prompt
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt="Abstract modern news broadcast background, professional studio setting, blue and white color scheme, minimalist design, geometric shapes, no text, no people",
                        n=1,
                        size="1024x1024"
                    )
                else:
                    raise

            image_url = response.data[0].url
            img_response = requests.get(image_url)
            img_response.raise_for_status()

            with open(thumb_path, "wb") as f:
                f.write(img_response.content)

            thumbnail_paths.append(str(thumb_path))

        print(f"[DEBUG] generate_thumbnails_node completed, generated {len(thumbnail_paths)} thumbnails")
        return {
            "thumbnails": thumbnail_paths,
            "status": "thumbnails_generated"
        }
    except Exception as e:
        print(f"[DEBUG] generate_thumbnails_node failed: {e}")
        return {"error": str(e), "status": "failed"}


def create_video_node(state: NewsVideoState) -> dict:
    print("[DEBUG] create_video_node starting...")
    if state.get("error"):
        return {}

    try:
        script_dir = Path(__file__).parent.parent / "video_agent"
        output_video_path = script_dir / "Story.mp4"

        story_count = state.get("story_count", 3)

        if story_count > 1:
            success = create_multi_story_video(
                audio_file=state["audio_path"],
                image_files=state["thumbnails"],
                story_boundaries=state["story_boundaries"],
                output_file=str(output_video_path)
            )
        else:
            create_video_with_word_captions(
                audio_file=state["audio_path"],
                image_file=state["thumbnails"][0],
                output_file=str(output_video_path)
            )
            success = True

        if not success:
            raise Exception("Video creation failed")

        print(f"[DEBUG] create_video_node completed, video at: {output_video_path}")
        return {
            "video_path": str(output_video_path),
            "status": "video_created"
        }
    except Exception as e:
        print(f"[DEBUG] create_video_node failed: {e}")
        return {"error": str(e), "status": "failed"}


def finalize_record_node(state: NewsVideoState) -> dict:
    print("[DEBUG] finalize_record_node starting...")
    if state.get("error"):
        return {}

    try:
        video_path = state['video_path']

        video_url = upload_video_to_storage(state["video_path"])
        thumbnail_url = upload_thumbnail_to_storage(state["thumbnails"][0])

        video_metadata = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "title": state["script_data"].get("title", "Daily News"),
            "summary": state["script"],
            "original_titles": state["script_data"].get("original_titles", []),
            "sources": state["script_data"].get("sources", []),
            "tags": state["script_data"].get("tags", [])
        }

        upload_video_metadata(video_metadata, video_url, thumbnail_url)

        # Clean up local files after successful upload
        # Delete video file
        if os.path.exists(state["video_path"]):
            os.remove(state["video_path"])
            print(f"[DEBUG] Deleted local video: {state['video_path']}")

        # Delete thumbnails
        for thumb in state["thumbnails"]:
            if os.path.exists(thumb):
                os.remove(thumb)
                print(f"[DEBUG] Deleted local thumbnail: {thumb}")

        # Delete audio file
        if os.path.exists(state["audio_path"]):
            os.remove(state["audio_path"])
            print(f"[DEBUG] Deleted local audio: {state['audio_path']}")

        # Delete script file
        if os.path.exists(state["script_path"]):
            os.remove(state["script_path"])
            print(f"[DEBUG] Deleted local script: {state['script_path']}")

        print("[DEBUG] finalize_record_node completed")
        return {"status": "completed"}

    except Exception as e:
        print(f"[DEBUG] finalize_record_node failed: {e}")
        return {"error": str(e), "status": "failed"}


def create_news_video_graph():
    workflow = StateGraph(NewsVideoState)

    workflow.add_node("fetch_news", fetch_news_node)
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("create_voiceover", create_voiceover_node)
    workflow.add_node("detect_boundaries", detect_boundaries_node)
    workflow.add_node("generate_thumbnails", generate_thumbnails_node)
    workflow.add_node("create_video", create_video_node)
    workflow.add_node("finalize_record", finalize_record_node)

    workflow.set_entry_point("fetch_news")
    workflow.add_edge("fetch_news", "generate_script")
    workflow.add_edge("generate_script", "create_voiceover")
    workflow.add_edge("create_voiceover", "detect_boundaries")
    workflow.add_edge("detect_boundaries", "generate_thumbnails")
    workflow.add_edge("generate_thumbnails", "create_video")
    workflow.add_edge("create_video", "finalize_record")
    workflow.add_edge("finalize_record", END)

    return workflow.compile()


def create_news_video_graph_with_checkpointing(db_path: str = "checkpoints.db"):

    workflow = StateGraph(NewsVideoState)

    workflow.add_node("fetch_news", fetch_news_node)
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("create_voiceover", create_voiceover_node)
    workflow.add_node("detect_boundaries", detect_boundaries_node)
    workflow.add_node("generate_thumbnails", generate_thumbnails_node)
    workflow.add_node("create_video", create_video_node)
    workflow.add_node("finalize_record", finalize_record_node)

    workflow.set_entry_point("fetch_news")
    workflow.add_edge("fetch_news", "generate_script")
    workflow.add_edge("generate_script", "create_voiceover")
    workflow.add_edge("create_voiceover", "detect_boundaries")
    workflow.add_edge("detect_boundaries", "generate_thumbnails")
    workflow.add_edge("generate_thumbnails", "create_video")
    workflow.add_edge("create_video", "finalize_record")
    workflow.add_edge("finalize_record", END)

    return workflow.compile()

def run_news_video_pipeline(story_count: int = 3):
    print("=" * 60)
    print("= HERMES AI News Video Pipeline")
    print("=" * 60)

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
    result = run_news_video_pipeline(story_count=3)