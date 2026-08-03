import os
import uuid
import tempfile
import shutil
import requests
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

progress_data = {}

INVIDIOUS_INSTANCES = [
    "https://vid.puffyan.us",
    "https://invidious.snopyta.org",
    "https://yewtu.be",
    "https://inv.riverside.rocks",
    "https://invidious.nerdvpn.de",
    "https://iv.ggtyler.dev",
]

def get_working_instance():
    for instance in INVIDIOUS_INSTANCES:
        try:
            r = requests.get(f"{instance}/api/v1/stats", timeout=5)
            if r.status_code == 200:
                return instance
        except:
            continue
    return INVIDIOUS_INSTANCES[0]

def extract_video_id(url):
    import re
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('public', path)

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'error': 'Could not extract video ID from URL'}), 400

    task_id = str(uuid.uuid4())[:8]
    tmp_dir = tempfile.mkdtemp()

    try:
        instance = get_working_instance()

        info_url = f"{instance}/api/v1/videos/{video_id}"
        info_resp = requests.get(info_url, timeout=10)
        if info_resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch video info'}), 400

        info = info_resp.json()
        title = info.get('title', 'audio').replace('/', '-').replace('\\', '-')

        adaptive_formats = info.get('adaptiveFormats', [])
        audio_streams = [f for f in adaptive_formats if f.get('type', '').startswith('audio/')]
        if not audio_streams:
            return jsonify({'error': 'No audio stream found'}), 400

        best_audio = audio_streams[0]
        audio_url = best_audio.get('url', '')
        if not audio_url:
            return jsonify({'error': 'Could not get audio URL'}), 400

        ext = 'webm'
        if 'opus' in best_audio.get('type', ''):
            ext = 'webm'
        elif 'mp4' in best_audio.get('type', '') or 'aac' in best_audio.get('type', ''):
            ext = 'm4a'

        filename = f"{title}.{ext}"
        file_path = os.path.join(tmp_dir, filename)

        audio_resp = requests.get(audio_url, timeout=60, stream=True)
        with open(file_path, 'wb') as f:
            for chunk in audio_resp.iter_content(chunk_size=8192):
                f.write(chunk)

        if os.path.getsize(file_path) == 0:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({'error': 'Downloaded file is empty'}), 400

        downloaded_files = [{
            'name': filename,
            'size': os.path.getsize(file_path),
            'task_id': task_id
        }]

        progress_data[task_id] = {
            'status': 'completed',
            'tmp_dir': tmp_dir,
            'files': downloaded_files
        }

        return jsonify({
            'task_id': task_id,
            'status': 'completed',
            'files': [{'name': f['name'], 'size': f['size']} for f in downloaded_files]
        })

    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({'error': str(e)[:200]}), 500

@app.route('/api/file/<task_id>/<filename>')
def download_file(task_id, filename):
    if task_id not in progress_data:
        return jsonify({'error': 'Task not found'}), 404

    tmp_dir = progress_data[task_id]['tmp_dir']
    file_path = os.path.join(tmp_dir, filename)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)

    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)