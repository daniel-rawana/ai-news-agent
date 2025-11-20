#!/usr/bin/env python3
"""
Script to view all video records stored in the database.
Provides filtering options by status, date, and headline search.
"""

import sys
from pathlib import Path

# Add database module to path
sys.path.append(str(Path(__file__).parent))
from video_database import (
    initialize_database,
    get_all_videos,
    get_videos_by_status,
    get_videos_by_date,
    get_videos_by_headline,
    get_db_path
)


def format_duration(seconds):
    """
    Formats duration in seconds to a readable string.
    
    Args:
        seconds: Duration in seconds (float or None)
    
    Returns:
        str: Formatted duration (e.g., "1m 23s") or "N/A"
    """
    if seconds is None:
        return "N/A"
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    
    if minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def display_video(video, index=None):
    """
    Displays a single video record in a formatted way.
    
    Args:
        video: Dictionary containing video record data
        index: Optional index number to display
    """
    prefix = f"[{index}] " if index is not None else ""
    
    print(f"\n{'='*80}")
    if index is not None:
        print(f"{prefix}Video ID: {video['id']}")
    else:
        print(f"Video ID: {video['id']}")
    
    print(f"Created: {video.get('created_at', 'N/A')}")
    print(f"Status: {video.get('status', 'N/A')}")
    print(f"Duration: {format_duration(video.get('duration'))}")
    
    if video.get('headline'):
        print(f"\nHeadline: {video['headline']}")
    
    if video.get('source'):
        print(f"Source: {video['source']}")
    
    if video.get('summary'):
        summary = video['summary']
        if len(summary) > 150:
            summary = summary[:150] + "..."
        print(f"\nSummary: {summary}")
    
    print(f"\nPaths:")
    print(f"  Script: {video.get('script_path', 'N/A')}")
    print(f"  Audio: {video.get('audio_path', 'N/A')}")
    if video.get('video_path'):
        print(f"  Video: {video['video_path']}")
    
    print(f"{'='*80}")


def display_all_videos():
    """Displays all videos in the database."""
    print("\n" + "="*80)
    print("ALL VIDEO RECORDS")
    print("="*80)
    
    videos = get_all_videos()
    
    if not videos:
        print("\nNo videos found in database.")
        return
    
    print(f"\nTotal videos: {len(videos)}\n")
    
    for i, video in enumerate(videos, 1):
        display_video(video, index=i)


def display_by_status(status):
    """Displays videos filtered by status."""
    print(f"\n" + "="*80)
    print(f"VIDEOS WITH STATUS: {status.upper()}")
    print("="*80)
    
    videos = get_videos_by_status(status)
    
    if not videos:
        print(f"\nNo videos found with status '{status}'.")
        return
    
    print(f"\nFound {len(videos)} video(s) with status '{status}':\n")
    
    for i, video in enumerate(videos, 1):
        display_video(video, index=i)


def display_by_date(date):
    """Displays videos created on a specific date."""
    print(f"\n" + "="*80)
    print(f"VIDEOS CREATED ON: {date}")
    print("="*80)
    
    videos = get_videos_by_date(date)
    
    if not videos:
        print(f"\nNo videos found for date '{date}'.")
        return
    
    print(f"\nFound {len(videos)} video(s) created on '{date}':\n")
    
    for i, video in enumerate(videos, 1):
        display_video(video, index=i)


def display_by_headline(search_term):
    """Displays videos matching a headline search."""
    print(f"\n" + "="*80)
    print(f"VIDEOS MATCHING HEADLINE: '{search_term}'")
    print("="*80)
    
    videos = get_videos_by_headline(search_term)
    
    if not videos:
        print(f"\nNo videos found matching '{search_term}'.")
        return
    
    print(f"\nFound {len(videos)} video(s) matching '{search_term}':\n")
    
    for i, video in enumerate(videos, 1):
        display_video(video, index=i)


def show_summary():
    """Shows a quick summary of all videos."""
    videos = get_all_videos()
    
    if not videos:
        print("\nNo videos in database.")
        return
    
    print("\n" + "="*80)
    print("DATABASE SUMMARY")
    print("="*80)
    print(f"\nTotal videos: {len(videos)}")
    
    # Count by status
    status_counts = {}
    for video in videos:
        status = video.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\nBy Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    # Show latest video
    if videos:
        print(f"\nLatest video:")
        print(f"  ID: {videos[0]['id']}")
        print(f"  Created: {videos[0].get('created_at', 'N/A')}")
        if videos[0].get('headline'):
            print(f"  Headline: {videos[0]['headline']}")
    print("="*80)


def main():
    """Main function with command-line argument handling."""
    # Initialize database and verify path
    db_path = get_db_path()
    print(f"Using database at: {db_path}")
    initialize_database()
    
    # Parse command-line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status' and len(sys.argv) > 2:
            display_by_status(sys.argv[2])
        elif command == 'date' and len(sys.argv) > 2:
            display_by_date(sys.argv[2])
        elif command == 'search' and len(sys.argv) > 2:
            search_term = ' '.join(sys.argv[2:])
            display_by_headline(search_term)
        elif command == 'summary':
            show_summary()
        elif command == 'help':
            print("""
Usage: python view_videos.py [command] [arguments]

Commands:
  (no args)           Show all videos
  summary             Show database summary statistics
  status <status>     Filter by status (processing/completed/failed)
  date <YYYY-MM-DD>  Filter by creation date
  search <term>      Search headlines for term
  help                Show this help message

Examples:
  python view_videos.py
  python view_videos.py summary
  python view_videos.py status processing
  python view_videos.py date 2024-11-01
  python view_videos.py search election
            """)
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' for usage information.")
    else:
        # No arguments - show all videos
        display_all_videos()


if __name__ == "__main__":
    main()

