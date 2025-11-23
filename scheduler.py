"""
Daily scheduler for automated news video generation.

This script runs the LangGraph orchestration pipeline on a schedule.
Configure the schedule below and run this script to start the scheduler.
"""

import sys
import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Add agents to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents', 'orchestration_agent'))

from orchestration_agent import run_news_video_pipeline


def daily_news_video_job():
    """Job function that runs the news video pipeline."""
    print(f"\n{'='*60}")
    print(f"⏰ Scheduled job started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    try:
        result = run_news_video_pipeline(story_count=4)

        if result.get("error"):
            print(f"❌ Job failed: {result['error']}")
        else:
            print(f"✅ Job completed successfully!")
            print(f"📹 Video: {result.get('video_path')}")

    except Exception as e:
        print(f"❌ Job error: {e}")


def start_scheduler(hour: int = 8, minute: int = 0):
    """
    Start the scheduler to run daily at the specified time.

    Args:
        hour: Hour to run (0-23). Default is 8 (8 AM).
        minute: Minute to run (0-59). Default is 0.
    """
    scheduler = BlockingScheduler()

    # Schedule daily job
    scheduler.add_job(
        daily_news_video_job,
        CronTrigger(hour=hour, minute=minute),
        id='daily_news_video',
        name='Daily News Video Generation',
        replace_existing=True
    )

    print(f"🗓️  Scheduler started!")
    print(f"📅 Daily job scheduled for {hour:02d}:{minute:02d}")
    print(f"Press Ctrl+C to stop\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹️  Scheduler stopped")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Schedule daily news video generation')
    parser.add_argument('--hour', type=int, default=8, help='Hour to run (0-23)')
    parser.add_argument('--minute', type=int, default=0, help='Minute to run (0-59)')
    parser.add_argument('--run-now', action='store_true', help='Run once immediately')

    args = parser.parse_args()

    if args.run_now:
        # Run immediately without scheduling
        daily_news_video_job()
    else:
        # Start the scheduler
        start_scheduler(hour=args.hour, minute=args.minute)