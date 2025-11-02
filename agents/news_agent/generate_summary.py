from fetch_news import fetch_news
from llm import summarize_story

stories = fetch_news(3)
# print(stories)
script = summarize_story(stories)
print(script)