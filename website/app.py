from dotenv import load_dotenv
load_dotenv()

import os
import sys
import threading
import uuid
import queue
from flask import Flask, render_template, url_for
from supabase import create_client
from datetime import date

# Add agents directory to path BEFORE importing orchestration_agent
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'agents', 'orchestration_agent'))
sys.path.insert(0, os.path.join(project_root, 'agents', 'news_agent'))
sys.path.insert(0, os.path.join(project_root, 'agents', 'video_agent'))
sys.path.insert(0, os.path.join(project_root, 'agents', 'database'))

from orchestration_agent import create_news_video_graph

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

app = Flask(__name__)

# Store active tasks and their status queues
active_tasks = {}

@app.context_processor
def inject_hermes_assets():
    return {
        'HermesLogo': url_for('static', filename='test-files/HermesLogoSoloTransparent.png'),
        'HermesName': url_for('static', filename='test-files/HermesLettersTransparent.png'),
        'BackgroundImage': url_for('static', filename='test-files/worldbackground.png')
    }

@app.route("/")
def index():
    response = supabase.table('videos').select('*').order('date', desc=True).execute()
    videos = response.data
    
    today = date.today().isoformat()  # Gets today's date as 'YYYY-MM-DD'
    
    # Look for a video with today's date
    todays_video = None
    for video in videos:
        if video['date'] == today and video['video_url']:
            todays_video = video
            break
    
    # If no video for today, use the latest one
    if todays_video is None:
        todays_video = videos[0] if videos else None
    
    return render_template('index.html', video=todays_video)

@app.route("/previousnews")
def previousnews():

    response = supabase.table('videos').select('id, thumbnail_url, summarized_title, date').execute()
    thumbnail_items = response.data

    
    seen_dates = set()
    news_items = []
    
    for item in thumbnail_items:
        if item['date'] not in seen_dates:
            seen_dates.add(item['date'])
            news_items.append(item)
    
    return render_template('previousnews.html', news_items=news_items)
    
@app.route("/sources")
def sources():
    return render_template('sources.html')

@app.route("/team")
def team():
    teamimg1 = url_for('static', filename='team_photos/DanielRawana.jpg')
    teamimg2 = url_for('static', filename='team_photos/RicknySanon.jpg')
    teamimg3 = url_for('static', filename='team_photos/EduardoGoncalvez.jpg')
    teamimg4 = url_for('static', filename='team_photos/GabrielRicadoAlamo.png')
    teamimg5 = url_for('static', filename='team_photos/RembertoSilva.jpg')
    teamimg6 = url_for('static', filename='team_photos/MohammedAlSaleh.jpg')
    teamimg7 = url_for('static', filename='team_photos/AlexWaisman.jpg')
    teamimg8 = url_for('static', filename='team_photos/JustinPalma.jpg')
    teamimg9 = url_for('static', filename='team_photos/jona.png')
    teamimg10 = url_for('static', filename='team_photos/AryanRahman.png')
    teamimg11 = url_for('static', filename='team_photos/RobertoMachin.png')
    teamimg13 = url_for('static', filename='team_photos/AlfonsinaCardenas.png')

    return render_template('team.html',pick1 = teamimg1,pick2 = teamimg2,pick3 = teamimg3,pick4 = teamimg4,pick5 = teamimg5,pick6 = teamimg6,pick7 = teamimg7,pick8 = teamimg8,pick9 = teamimg9,pick10 = teamimg10,pick11 = teamimg11,pick13 = teamimg13)

@app.route("/video/<int:id>")
def video(id):

    response = supabase.table('videos').select('video_url').eq('id', id).execute()
    video_data = response.data
    video_url = video_data[0]['video_url'] if video_data else None
    return render_template('video.html', video=video_url)

if __name__ == "__main__":
    # debug=True helps during development (auto-reload and better error pages)
    app.run(debug=True)