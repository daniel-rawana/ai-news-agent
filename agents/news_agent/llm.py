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

    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    client = OpenAI(api_key=OPENAI_API_KEY)

    content = story['stories'][0]
    user_content = "Story to summarize:\n\n"
    user_content += (
        f"Headline: {content['headline']}\n"
        f"Summary: {content['summary']}\n"
        f"Source: {content['source']}\n\n"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role" :"system", "content": system_prompt},
            {"role": "user", "content": user_content}],
    )

    script = response.choices[0].message.content

    return script 
