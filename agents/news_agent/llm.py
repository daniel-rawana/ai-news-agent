import requests
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import os
from pathlib import Path

def summarize_story(story):

    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

    if isinstance(story, str):
        story = json.loads(story)
    
    # Validate story structure
    if 'stories' not in story or not story.get('stories'):
        raise ValueError("No stories found in the provided data. Cannot generate summary.")

    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    prompt_path = script_dir / "system_prompt.txt"
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Safely access the first story
    if len(story['stories']) == 0:
        raise ValueError("Stories list is empty.")
    
    content = story['stories'][0]
    user_content = "Story to summarize:\n\n"
    user_content += (
        f"Headline: {content.get('headline', 'No headline')}\n"
        f"Summary: {content.get('summary', 'No summary')}\n"
        f"Source: {content.get('source', 'Unknown source')}\n\n"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role" :"system", "content": system_prompt},
            {"role": "user", "content": user_content}],
    )

    script = response.choices[0].message.content

    return script 
