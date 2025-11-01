from gtts import gTTS
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
import sys

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


video_agent_dir = os.getcwd()
news_agent_dir = os.path.join(os.path.dirname(__file__), '../news_agent')
os.chdir(news_agent_dir)

sys.path.append('../news_agent')
from fetch_news import fetch_news
from llm import summarize_story


stories=fetch_news(1)
script=summarize_story(stories)
print(script)

os.chdir(video_agent_dir)

with open("Story.txt", "w") as file:
    file.write(script)

tts = gTTS(text=script, lang='en')

tts.save('Story.mp3')

img_prompt = f"Create a professional news thumbnail image for this story: {script}. Style: modern news broadcast, clean, professional, high quality"
try:
    response = client.images.generate(
        model="dall-e-3",
        prompt=img_prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url
    print(image_url)

    imagefile = "thumbnail.png"
    response = requests.get(image_url)
    with open(imagefile, "wb") as f:
        f.write(response.content)
except Exception as e:
    print(f"Error generating image: {e}")


print("Video generation done")