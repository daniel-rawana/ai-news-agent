import json
from fetch_news import fetch_news
from llm import summarize_story


def generate_news_script(story_count=1, return_metadata=False):
    """
    Fetches news stories and generates a summarized script.
    
    Args:
        story_count (int): Number of news stories to fetch. Default is 1.
        return_metadata (bool): If True, returns dict with script and metadata. Default is False.
    
    Returns:
        str or dict: 
            - If return_metadata=False: The generated news script string
            - If return_metadata=True: Dict with 'script' and 'story_metadata' keys
    """
    stories_json = fetch_news(story_count)
    
    # Check if fetch_news returned an error
    try:
        stories_data = json.loads(stories_json)
        if 'error' in stories_data:
            error_msg = (
                f"Failed to generate news script.\n"
                f"Error: {stories_data.get('error', 'Unknown error')}\n"
                f"Please check the error messages above for details."
            )
            return error_msg if not return_metadata else {'script': error_msg, 'story_metadata': None}
        
        # Check if there are no stories
        if not stories_data.get('stories') or len(stories_data['stories']) == 0:
            error_msg = "No news stories available to summarize."
            return error_msg if not return_metadata else {'script': error_msg, 'story_metadata': None}
        
        # Extract metadata from first story
        story_metadata = stories_data['stories'][0] if stories_data['stories'] else None
        
    except json.JSONDecodeError:
        error_msg = f"Failed to parse news data. Raw response: {stories_json[:200]}"
        return error_msg if not return_metadata else {'script': error_msg, 'story_metadata': None}
    
    # Generate summary if we have valid stories
    try:
        script = summarize_story(stories_json)
        if return_metadata:
            return {
                'script': script,
                'story_metadata': story_metadata
            }
        return script
    except Exception as e:
        error_msg = f"Failed to generate summary: {str(e)}"
        return error_msg if not return_metadata else {'script': error_msg, 'story_metadata': story_metadata}


# Allow running as a standalone script
if __name__ == "__main__":
    script = generate_news_script(1)
    print(script)
