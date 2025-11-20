from agents.orchestration_agent.orchestration_agent import fetch_news_node

mock_state = {
    "stories": [],
    "script": "",
    "audio_path": "",
    "thumbnails": [],
    "video_path": "",
    "error": None,
    "status": ""
}

result = fetch_news_node(mock_state)
print(result)