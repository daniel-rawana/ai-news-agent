import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os

def fetch_news(count):
    load_dotenv()
    API_KEY = os.getenv("API_KEY")

    url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=10&apiKey={API_KEY}"

    response = requests.get(url)
    data = response.json()

    today = datetime.now().strftime("%Y-%m-%d")

    structured_output = {
        "date": today,
        "stories": []
    }

    for article in data['articles']:
        if article.get('description') is None or article.get('description') == '':
            continue
        story = {
            "headline": article['title'],
            "summary": article['description'],
            "source": article['source']['name'],
            "url": article['url'],
            "image": article['urlToImage']
        }
        structured_output['stories'].append(story)

        if len(structured_output['stories']) == count:
            break

    return json.dumps(structured_output, indent=2)