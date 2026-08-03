import os
import uuid
import tempfile
import shutil
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

progress_data = {}

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

    task_id = str(uuid.uuid4())[:8]
    tmp_dir = tempfile.mkdtemp()

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        downloaded_files = []
        for f in os.listdir(tmp_dir):
            file_path = os.path.join(tmp_dir, f)
            if os.path.isfile(file_path):
                downloaded_files.append({
                    'name': f,
                    'size': os.path.getsize(file_path),
                    'task_id': task_id
                })

        if not downloaded_files:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({'error': 'No downloadable content found'}), 400

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
        return jsonify({'error': str(e)}), 400

@app.route('/api/file/<task_id>/<filename>')
def download_file(task_id, filename):
    if task_id not in progress_data:
        return jsonify({'error': 'Task not found'}), 404

    tmp_dir = progress_data[task_id]['tmp_dir']
    file_path = os.path.join(tmp_dir, filename)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)

    return jsonify({'error': 'File not found'}), 404

from flask import send_file

if __name__ == '__main__':
    app.run(debug=True, port=5000)