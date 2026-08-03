import os
import uuid
import tempfile
import shutil
from flask import Flask, request, jsonify, send_from_directory, send_file
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
        output_path = os.path.join(tmp_dir, '%(title)s.%(ext)s')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if info is None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({'error': 'Could not retrieve video info. Check the URL.'}), 400

        downloaded_files = []
        for f in os.listdir(tmp_dir):
            file_path = os.path.join(tmp_dir, f)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                if size > 0:
                    downloaded_files.append({
                        'name': f,
                        'size': size,
                        'task_id': task_id
                    })

        if not downloaded_files:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({'error': 'Download failed. The video may be private or restricted.'}), 400

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

    except yt_dlp.utils.DownloadError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({'error': f'Download error: {str(e)[:200]}'}), 400
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({'error': f'Server error: {str(e)[:200]}'}), 500

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