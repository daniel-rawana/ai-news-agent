from fetch_news import fetch_news
from llm import summarize_story

stories = fetch_news(1)
script = summarize_story(stories)

print(script)