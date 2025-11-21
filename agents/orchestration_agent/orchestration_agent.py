from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
import json
import operator

class NewsVideoState(TypedDict, total=False):
    stories: List[dict]
    original_titles: List[str]
    summary: dict
    error: Optional[str]
    status: str

def fetch_news_node(state: NewsVideoState) -> NewsVideoState:
    from agents.news_agent.fetch_news import fetch_news
    response = json.loads(fetch_news(count=3))

    return {"stories": response["stories"], "status": "news_fetched"}

def generate_script_node(state: NewsVideoState) -> NewsVideoState:
    from agents.news_agent.llm import summarize_story

    response = summarize_story(state)

    return {"summary": response, "status": "script_generated"}