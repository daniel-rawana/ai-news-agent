import requests
import json
from datetime import datetime

API_KEY = "67acfe5e58a948f8a46fdd3d93ee1d3f"

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
        "source": article['source']['name']
    }
    structured_output['stories'].append(story)

    if len(structured_output['stories']) == 3:
        break


print(json.dumps(structured_output, indent=2))
