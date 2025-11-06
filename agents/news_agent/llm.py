import requests
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import os


def summarize_story(story):

    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if isinstance(story, str):
        story = json.loads(story)

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
