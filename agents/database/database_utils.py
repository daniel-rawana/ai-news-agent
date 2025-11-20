import os
import supabase
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from pathlib import Path

# Import from same directory
from video_database import get_videos_by_status

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client():

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY in .env"
        )
    return supabase.create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all_videos():

    client = get_supabase_client()

    response = client.table("videos").select(
        "*, " \
        "original_titles(*), " \
        "video_sources(sources(*)), " \
        "video_tags(tags(*))"
    ).execute()

    return response.data or []

def upload_video_to_storage(video_path):

    client = get_supabase_client()

    if not video_path:
        raise ValueError(f"Video record has no video_path")

    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    filename = video_file.stem  
    if filename == "Story":
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    else:
        timestamp = filename.split("_", 1)[-1] if "_" in filename else filename

    storage_path = f"videos/{timestamp}.mp4"  

    with open(video_file, "rb") as f:
        file_data = f.read()

        response = client.storage.from_("media").upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "video/mp4"}
        )

    public_url = client.storage.from_("media").get_public_url(storage_path)

    return public_url

def upload_thumbnail_to_storage(image_path):

    client = get_supabase_client()

    if not image_path:
        raise ValueError(f"Image has no image_path")
    
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    filename = image_file.stem  
    if filename == "thumbnail":
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    else:
        timestamp = filename.split("_", 1)[-1] if "_" in filename else filename

    storage_path = f"thumbnails/{timestamp}.png" 

    with open(image_file, "rb") as f:
        file_data = f.read()

        response = client.storage.from_("media").upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "image/png"}
        )

    public_url = client.storage.from_("media").get_public_url(storage_path)

    return public_url

def upload_video_metadata(news_data, video_url= None, thumbnail_url=None):

    client = get_supabase_client()

    date = news_data["date"]
    title = news_data["title"]
    summary = news_data["summary"]

    response = client.table("videos").insert({
        "date": date,
        "summarized_title": title,
        "summary": summary,
        "video_url": video_url,
        "thumbnail_url": thumbnail_url
    }).execute()

    if response.data and len(response.data) > 0:
        video_id = response.data[0]["id"]
    else:
        raise Exception("Failed to insert video metadata in videos table")

    # TODO Modify this once news team completes original titles task
    if news_data.get("original_titles"):
        for position, title in enumerate(news_data["original_titles"]):
            client.table("original_titles").insert({
                "video_id": video_id,
                "title": title,
                "position": position
            }).execute()

    for source_data in news_data["sources"]:
        source_name = source_data["name"]
        source_url = source_data["url"]

        existing_source = client.table("sources")\
            .select("*")\
            .eq("name", source_name)\
            .execute()

        if existing_source.data and len(existing_source.data) > 0:
            source_id = existing_source.data[0]["id"]
        else:
            new_source = client.table("sources").insert({
                "name": source_name,
                "base_url": source_url
            }).execute()
            source_id = new_source.data[0]["id"]

        client.table("video_sources").insert({
            "video_id": video_id,
            "source_id": source_id,
            "article_url": source_url 
        }).execute()

    for tag_name in news_data["tags"]:
        existing_tag = client.table("tags")\
            .select("*")\
            .eq("name", tag_name)\
            .execute()
        
        if existing_tag.data and len(existing_tag.data) > 0:
            tag_id = existing_tag.data[0]["id"]
        else:
            new_tag = client.table("tags").insert({
                "name": tag_name
            }).execute()
            tag_id = new_tag.data[0]["id"]
        
        client.table("video_tags").insert({
            "video_id": video_id,
            "tag_id": tag_id
        }).execute()

    return video_id
