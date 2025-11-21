import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.orchestration_agent.orchestration_agent import fetch_news_node, NewsVideoState, generate_script_node

mock_state: NewsVideoState = {
    "stories": [],
    "original_titles": [],
    "summary": {},
    "error": None,
    "status": ""
}

result = fetch_news_node(mock_state)

# print(result["stories"])

result = generate_script_node(result)

print(result)