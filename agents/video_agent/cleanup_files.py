#!/usr/bin/env python3
"""
Cleanup script to move script and audio files from agents/video_agent/ 
to agents/video_agent/voiceovers/ subfolder.

This script moves:
- script_*.txt files
- voiceover_*.mp3 files
- Story.txt
- Story.mp3

All files are moved from agents/video_agent/ to agents/video_agent/voiceovers/
"""

import os
import shutil
from pathlib import Path


def cleanup_files():
    """
    Moves script and audio files from agents/video_agent/ to agents/video_agent/voiceovers/
    """
    # Get the script directory (agents/video_agent/)
    script_dir = Path(__file__).parent.resolve()
    voiceovers_dir = script_dir / "voiceovers"
    
    # Ensure voiceovers directory exists
    voiceovers_dir.mkdir(exist_ok=True)
    
    print(f"Source directory: {script_dir}")
    print(f"Target directory: {voiceovers_dir}")
    print("=" * 60)
    
    # Patterns to search for
    patterns = [
        "script_*.txt",
        "voiceover_*.mp3",
        "Story.txt",
        "Story.mp3"
    ]
    
    files_moved = []
    files_failed = []
    
    # Find and move files matching patterns
    for pattern in patterns:
        # Search in script_dir only (not recursively)
        matches = list(script_dir.glob(pattern))
        
        for file_path in matches:
            # Skip if file is already in voiceovers directory
            if voiceovers_dir in file_path.parents:
                continue
            
            # Skip if it's this script itself
            if file_path.name == "cleanup_files.py":
                continue
            
            try:
                # Check if file exists
                if not file_path.exists():
                    print(f"⚠️  File not found (may have been deleted): {file_path.name}")
                    continue
                
                # Destination path
                dest_path = voiceovers_dir / file_path.name
                
                # Check if destination file already exists
                if dest_path.exists():
                    print(f"⚠️  File already exists in voiceovers/: {file_path.name}")
                    print(f"   Skipping to avoid overwriting existing file.")
                    continue
                
                # Move the file
                print(f"Moving: {file_path.name}")
                print(f"  From: {file_path}")
                print(f"  To:   {dest_path}")
                
                shutil.move(str(file_path), str(dest_path))
                files_moved.append(file_path.name)
                
            except Exception as e:
                error_msg = f"❌ Failed to move {file_path.name}: {e}"
                print(error_msg)
                files_failed.append((file_path.name, str(e)))
    
    # Summary
    print("=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    
    if files_moved:
        print(f"✓ Successfully moved {len(files_moved)} file(s):")
        for filename in files_moved:
            print(f"  - {filename}")
    else:
        print("ℹ️  No files found to move.")
    
    if files_failed:
        print(f"\n✗ Failed to move {len(files_failed)} file(s):")
        for filename, error in files_failed:
            print(f"  - {filename}: {error}")
    
    if files_moved or files_failed:
        print()
    
    print(f"All files should now be in: {voiceovers_dir}")
    
    return len(files_moved), len(files_failed)


if __name__ == "__main__":
    print("=" * 60)
    print("CLEANUP: Moving files to voiceovers/ directory")
    print("=" * 60)
    print()
    
    try:
        moved_count, failed_count = cleanup_files()
        
        if failed_count == 0:
            if moved_count > 0:
                print("\n✓ Cleanup completed successfully!")
            else:
                print("\n✓ No files needed to be moved.")
        else:
            print(f"\n⚠️  Cleanup completed with {failed_count} error(s).")
            
    except Exception as e:
        print(f"\n❌ Cleanup failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

