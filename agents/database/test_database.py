import database_utils
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "news_agent"))

from generate_summary import generate_news_script

def main():
    video_path = Path(__file__).parent.parent / "video_agent" / "Story.mp4"

    video_url = database_utils.upload_video_to_storage(str(video_path))
    
    print(f"Public URL: {video_url}")

    image_path = Path(__file__).parent.parent / "video_agent" / "thumbnail.png"

    image_url = database_utils.upload_thumbnail_to_storage(str(image_path))

    print(f"Public URL: {image_url}")

    script = generate_news_script(3)

    videoID = database_utils.upload_video_metadata(script, video_url, image_url)

    print(f"Video uploaded successfully! ID: {videoID}")

    database = database_utils.fetch_all_videos()
    print(json.dumps(database, indent=2))

if __name__ == "__main__":
    main()