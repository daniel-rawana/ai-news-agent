import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import sys

def fetch_news(count):
    """
    Fetches news articles from NewsAPI.
    
    Args:
        count (int): Number of news stories to fetch
    
    Returns:
        str: JSON string containing structured news data, or error message
    """
    # Load environment variables
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    
    # Check if API_KEY is loaded
    if not API_KEY:
        error_msg = (
            "ERROR: API_KEY not found in environment variables.\n"
            "Please check your .env file and ensure it contains:\n"
            "API_KEY=your_newsapi_key_here\n"
            "Get your API key at: https://newsapi.org/register"
        )
        print(error_msg, file=sys.stderr)
        return json.dumps({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stories": [],
            "error": "API_KEY not found"
        }, indent=2)
    
    # Construct API URL
    url = f"https://newsapi.org/v2/top-headlines?country=us&pageSize=10&apiKey={API_KEY}"
    
    # Make API request with error handling
    try:
        print(f"Fetching news from NewsAPI...")
        response = requests.get(url, timeout=10)
        print(f"API Response Status Code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code != 200:
            error_msg = (
                f"ERROR: NewsAPI request failed with status code {response.status_code}\n"
                f"Response: {response.text}"
            )
            print(error_msg, file=sys.stderr)
            
            # Try to parse error message from response
            try:
                error_data = response.json()
                if 'message' in error_data:
                    print(f"API Error Message: {error_data['message']}", file=sys.stderr)
                    if error_data.get('code') == 'apiKeyInvalid':
                        print("SOLUTION: Your API key is invalid. Please check your .env file.", file=sys.stderr)
                    elif error_data.get('code') == 'rateLimited':
                        print("SOLUTION: You've exceeded the rate limit. Wait a moment and try again.", file=sys.stderr)
            except json.JSONDecodeError:
                pass
            
            return json.dumps({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "stories": [],
                "error": f"API request failed with status {response.status_code}"
            }, indent=2)
        
        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            error_msg = f"ERROR: Failed to parse API response as JSON: {e}\nResponse text: {response.text[:500]}"
            print(error_msg, file=sys.stderr)
            return json.dumps({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "stories": [],
                "error": "Failed to parse API response"
            }, indent=2)
        
        # Check if response contains 'articles' key
        if 'articles' not in data:
            error_msg = (
                f"ERROR: API response missing 'articles' key.\n"
                f"Response structure: {json.dumps(data, indent=2)[:500]}"
            )
            print(error_msg, file=sys.stderr)
            
            # Check for common error codes in the response
            if 'status' in data and data.get('status') == 'error':
                if 'message' in data:
                    print(f"API Error: {data['message']}", file=sys.stderr)
                if 'code' in data:
                    code = data['code']
                    print(f"Error Code: {code}", file=sys.stderr)
                    if code == 'apiKeyInvalid':
                        print("SOLUTION: Your API key is invalid. Check your .env file.", file=sys.stderr)
                    elif code == 'rateLimited':
                        print("SOLUTION: Rate limit exceeded. Wait before retrying.", file=sys.stderr)
                    elif code == 'apiKeyMissing':
                        print("SOLUTION: API key is missing from the request.", file=sys.stderr)
            
            return json.dumps({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "stories": [],
                "error": "API response missing 'articles' key",
                "api_response": data
            }, indent=2)
        
        # Check if articles list is empty
        if not data.get('articles'):
            print("WARNING: API returned empty articles list.", file=sys.stderr)
            return json.dumps({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "stories": [],
                "error": "No articles found in API response"
            }, indent=2)
        
        # Process articles
        today = datetime.now().strftime("%Y-%m-%d")
        structured_output = {
            "date": today,
            "stories": []
        }
        
        articles_processed = 0
        for article in data['articles']:
            # Skip articles without descriptions
            if article.get('description') is None or article.get('description') == '':
                continue
            
            # Safely extract article data
            try:
                story = {
                    "headline": article.get('title', 'No title'),
                    "summary": article.get('description', 'No description'),
                    "source": article.get('source', {}).get('name', 'Unknown source')
                }
                structured_output['stories'].append(story)
                articles_processed += 1
                
                if articles_processed >= count:
                    break
            except Exception as e:
                print(f"WARNING: Error processing article: {e}", file=sys.stderr)
                continue
        
        if articles_processed == 0:
            print("WARNING: No valid articles with descriptions found.", file=sys.stderr)
        
        print(f"Successfully fetched {len(structured_output['stories'])} news story/stories.")
        return json.dumps(structured_output, indent=2)
    
    except requests.exceptions.Timeout:
        error_msg = "ERROR: Request to NewsAPI timed out. Please check your internet connection."
        print(error_msg, file=sys.stderr)
        return json.dumps({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stories": [],
            "error": "API request timed out"
        }, indent=2)
    
    except requests.exceptions.ConnectionError:
        error_msg = "ERROR: Failed to connect to NewsAPI. Please check your internet connection."
        print(error_msg, file=sys.stderr)
        return json.dumps({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stories": [],
            "error": "Connection error"
        }, indent=2)
    
    except Exception as e:
        error_msg = f"ERROR: Unexpected error occurred: {type(e).__name__}: {e}"
        print(error_msg, file=sys.stderr)
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        return json.dumps({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stories": [],
            "error": f"Unexpected error: {str(e)}"
        }, indent=2)


# Test the function when run directly
if __name__ == "__main__":
    print("=" * 60)
    print("Testing fetch_news() function")
    print("=" * 60)
    print()
    
    result_json = fetch_news(1)
    
    # Parse and display the result
    try:
        result = json.loads(result_json)
        
        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print()
        
        # Check if result has data or errors
        if 'error' in result:
            print("=" * 60)
            print("STATUS: ERROR DETECTED")
            print("=" * 60)
            print(f"Error: {result['error']}")
        elif result.get('stories'):
            story_count = len(result['stories'])
            print("=" * 60)
            print(f"STATUS: SUCCESS - {story_count} story/stories found")
            print("=" * 60)
            print(f"Date: {result.get('date', 'N/A')}")
            print(f"Number of stories: {story_count}")
        else:
            print("=" * 60)
            print("STATUS: NO DATA")
            print("=" * 60)
            print("The function returned successfully but no stories were found.")
            
    except json.JSONDecodeError:
        print("\n" + "=" * 60)
        print("ERROR: Failed to parse result as JSON")
        print("=" * 60)
        print(f"Raw output: {result_json[:500]}")
    
    print("\n" + "=" * 60)
