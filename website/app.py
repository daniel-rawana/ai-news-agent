from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask, render_template, url_for
from supabase import create_client
from datetime import date

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

app = Flask(__name__)

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
    linknews1 = url_for('static', filename='test-files/one.jpeg')
    linknews2 = url_for('static', filename='test-files/two.jpg')
    linknews3 = url_for('static', filename='test-files/three.webp')
    linknews4 = url_for('static', filename='test-files/four.jpg')
    linknews5 = url_for('static', filename='test-files/five.webp')
    linknews6 = url_for('static', filename='test-files/six.jpg')
    linknews7 = url_for('static', filename='test-files/seven.webp')
    linknews8 = url_for('static', filename='test-files/eight.webp')
    linknews9 = url_for('static', filename='test-files/nine.webp')

    return render_template('team.html',news1 = linknews1,news2 = linknews2,news3 = linknews3,news4 = linknews4,news5 = linknews5,news6 = linknews6,news7 = linknews7,news8 = linknews8,news9 = linknews9)

@app.route("/video/<int:id>")
def video(id):

    response = supabase.table('videos').select('video_url').eq('id', id).execute()
    video_data = response.data
    video_url = video_data[0]['video_url'] if video_data else None
    return render_template('video.html', video=video_url)

if __name__ == "__main__":
    # debug=True helps during development (auto-reload and better error pages)
    app.run(debug=True)