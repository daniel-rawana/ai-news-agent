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

    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()

        client = OpenAI(api_key=OPENAI_API_KEY)

        stories = story['stories'][:3]
        user_content = "Stories to summarize:\n\n"
        for i, content in enumerate(stories, 1):
            user_content += (
                f"Story {i}:\n"
                f"Headline: {content['headline']}\n"
                f"Summary: {content['summary']}\n"
                f"Source: {content['source']}\n\n"
            )

        today = datetime.now().strftime("%Y-%m-%d")
        user_content += f"\nToday's date is: {today}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}],
            response_format={"type": "json_object"}
        )

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
        script = response.choices[0].message.content

        return json.loads(script)
    except Exception as e:
        today = datetime.now().strftime("%Y-%m-%d")
        stories = story['stories'][:3]
        response = {
            "date": today,
            "stories": [
                {
                    "title": content['headline'],
                    "summary": content['summary'],
                    "source": {
                        "name": content['source'],
                        "url": content['url'],


                    }
                }
                for content in stories
            ]
        }
        return response
