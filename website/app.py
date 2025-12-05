from dotenv import load_dotenv
load_dotenv()

import os
import sys
import threading
import uuid
import queue
from flask import Flask, render_template, url_for, request, jsonify, Response
from supabase import create_client

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
    mainvideo = supabase.table('videos').select('*').execute()
    videos = mainvideo.data

    video_url = videos[0]['video_url'] if videos else None

    return render_template('index.html', video=video_url)

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

@app.route("/agent")
def agent():
    return render_template('agent.html')

@app.route("/agent/generate", methods=['POST'])
def generate_video():
    """Start video generation process"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400
        category = data.get('category', 'general')

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Create a queue for this task
        status_queue = queue.Queue()
        active_tasks[task_id] = {
            'queue': status_queue,
            'category': category,
            'video_url': None,
            'error': None
        }

        # Start video generation in background thread
        thread = threading.Thread(
            target=run_video_generation,
            args=(task_id, category, status_queue)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'task_id': task_id}), 202

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/agent/status/<task_id>")
def video_status(task_id):
    """Polling endpoint for status updates"""
    if task_id not in active_tasks:
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404

    task = active_tasks[task_id]

    # Get the most recent status from the task
    current_status = task.get('current_status', 'starting')
    video_url = task.get('video_url')
    error = task.get('error')

    response_data = {'status': current_status}

    if video_url:
        response_data['video_url'] = video_url

    if error:
        response_data['message'] = error
        response_data['status'] = 'error'

    print(f"[POLL] Task {task_id} status: {current_status}")

    return jsonify(response_data)

def run_video_generation(task_id, category, status_queue):
    """Run the video generation pipeline and send status updates"""
    try:
        # Update task status
        if task_id in active_tasks:
            active_tasks[task_id]['current_status'] = 'starting'

        # Create graph
        graph = create_news_video_graph()

        # Initial state with category
        initial_state = {
            "story_count": 3,
            "category": category,
            "stories": [],
            "script": "",
            "script_data": {},
            "audio_path": "",
            "script_path": "",
            "timestamp": "",
            "thumbnails": [],
            "story_boundaries": [],
            "story_segments": [],
            "video_path": "",
            "video_id": None,
            "duration": None,
            "error": None,
            "status": "starting"
        }

        # Execute graph and track state changes
        print(f"[WEBAPP] Starting graph execution for task {task_id}")

        # Execute graph
        current_state = initial_state
        for output in graph.stream(current_state):
            print(f"[WEBAPP] Graph stream output: {list(output.keys())}")
            # Extract the node and its updated state
            for node_name, node_output in output.items():
                print(f"[WEBAPP] Node {node_name} output: {node_output.get('status', 'no status')}")
                current_state.update(node_output)

                # Update task status
                if 'status' in node_output and task_id in active_tasks:
                    print(f"[WEBAPP] Updating status to: {node_output['status']}")
                    active_tasks[task_id]['current_status'] = node_output['status']

                # Check for errors
                if node_output.get('error'):
                    print(f"[WEBAPP] Error detected: {node_output['error']}")
                    if task_id in active_tasks:
                        active_tasks[task_id]['error'] = node_output['error']
                        active_tasks[task_id]['current_status'] = 'error'
                    return

        # Get the video URL from the database (most recent upload)
        print("[WEBAPP] Fetching video URL from database")
        mainvideo = supabase.table('videos').select('video_url').order('id', desc=True).limit(1).execute()
        video_url = mainvideo.data[0]['video_url'] if mainvideo.data else None
        print(f"[WEBAPP] Video URL: {video_url}")

        # Update task with completion status
        if task_id in active_tasks:
            active_tasks[task_id]['current_status'] = 'completed'
            active_tasks[task_id]['video_url'] = video_url

        print(f"[WEBAPP] Task {task_id} completed successfully")

    except Exception as e:
        error_msg = str(e)
        print(f"[WEBAPP] Exception in run_video_generation: {error_msg}")
        import traceback
        traceback.print_exc()
        if task_id in active_tasks:
            active_tasks[task_id]['error'] = error_msg
            active_tasks[task_id]['current_status'] = 'error'

if __name__ == "__main__":
    # debug=True helps during development (auto-reload and better error pages)
    app.run(debug=True)