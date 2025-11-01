import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


def get_db_path() -> Path:
    """
    Get the absolute path to the database file in project root.
    This ensures ALL scripts use the same database location.
    
    Returns:
        Path: Absolute path to news_videos.db in the project root
    """
    # Get the absolute path of this file first to ensure consistency
    # agents/database/video_database.py -> agents/database -> agents -> project_root
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    return project_root / "news_videos.db"


# Database file path (project root) - use function to ensure consistency
DB_PATH = get_db_path()


def get_db_connection():
    """
    Creates and returns a connection to the SQLite database.
    Always uses absolute path to ensure consistency regardless of working directory.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    # Always use absolute path to prevent SQLite from creating db in wrong location
    db_path = get_db_path().resolve()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def initialize_database():
    """
    Initializes the database and creates the 'videos' table if it doesn't exist.
    This function is safe to call multiple times (idempotent).
    """
    db_path = get_db_path()
    
    # Ensure the directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            script_path TEXT NOT NULL,
            audio_path TEXT NOT NULL,
            video_path TEXT,
            headline TEXT,
            summary TEXT,
            source TEXT,
            duration REAL,
            status TEXT NOT NULL DEFAULT 'processing',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {db_path}")


def insert_video_record(
    timestamp: str,
    script_path: str,
    audio_path: str,
    video_path: Optional[str] = None,
    headline: Optional[str] = None,
    summary: Optional[str] = None,
    source: Optional[str] = None,
    duration: Optional[float] = None,
    status: str = "processing"
) -> int:
    """
    Inserts a new video record into the database.
    
    Args:
        timestamp: Timestamp string (format: YYYYMMDD_HHMMSS)
        script_path: Path to the .txt script file
        audio_path: Path to the .mp3 voiceover file
        video_path: Optional path to video file
        headline: Optional news headline
        summary: Optional summary text
        source: Optional news source name
        duration: Optional duration in seconds
        status: Status of the video (default: "processing")
    
    Returns:
        int: The ID of the newly inserted record
    """
    initialize_database()  # Ensure table exists
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Convert timestamp to datetime for created_at
    try:
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO videos (
            timestamp, script_path, audio_path, video_path,
            headline, summary, source, duration, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, script_path, audio_path, video_path,
        headline, summary, source, duration, status, created_at
    ))
    
    video_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return video_id


def get_all_videos() -> List[Dict[str, Any]]:
    """
    Retrieves all video records from the database.
    
    Returns:
        List[Dict]: List of video records as dictionaries
    """
    initialize_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM videos ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    conn.close()
    
    return [dict(row) for row in rows]


def get_videos_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Retrieves videos filtered by status.
    
    Args:
        status: Status to filter by (e.g., 'processing', 'completed', 'failed')
    
    Returns:
        List[Dict]: List of matching video records
    """
    initialize_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM videos 
        WHERE status = ? 
        ORDER BY created_at DESC
    """, (status,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_videos_by_date(date: str) -> List[Dict[str, Any]]:
    """
    Retrieves videos created on a specific date.
    
    Args:
        date: Date string in format 'YYYY-MM-DD' or 'YYYYMMDD'
    
    Returns:
        List[Dict]: List of matching video records
    """
    initialize_database()
    
    # Normalize date format
    if len(date) == 8 and '-' not in date:
        # Format: YYYYMMDD -> YYYY-MM-DD
        date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM videos 
        WHERE DATE(created_at) = ? 
        ORDER BY created_at DESC
    """, (date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_videos_by_headline(headline_search: str) -> List[Dict[str, Any]]:
    """
    Retrieves videos where headline contains the search term.
    
    Args:
        headline_search: Search term to match in headline
    
    Returns:
        List[Dict]: List of matching video records
    """
    initialize_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM videos 
        WHERE headline LIKE ? 
        ORDER BY created_at DESC
    """, (f"%{headline_search}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def update_video_status(video_id: int, status: str) -> bool:
    """
    Updates the status of a video record.
    
    Args:
        video_id: ID of the video to update
        status: New status value
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    initialize_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE videos 
        SET status = ? 
        WHERE id = ?
    """, (status, video_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def update_video_path(video_id: int, video_path: str) -> bool:
    """
    Updates the video_path of a video record.
    
    Args:
        video_id: ID of the video to update
        video_path: Path to the video file
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    initialize_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE videos 
        SET video_path = ? 
        WHERE id = ?
    """, (video_path, video_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def get_video_by_id(video_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single video record by ID.
    
    Args:
        video_id: ID of the video to retrieve
    
    Returns:
        Dict: Video record as dictionary, or None if not found
    """
    initialize_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    return dict(row) if row else None


def delete_video(video_id: int) -> bool:
    """
    Deletes a video record from the database.
    
    Args:
        video_id: ID of the video to delete
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    initialize_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success

