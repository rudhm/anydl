from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import os
import threading
import uuid
import re

app = Flask(__name__, static_folder='.')

DOWNLOAD_DIR = os.path.expanduser('~/Downloads/AnyDL')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

downloads = {}
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class MyLogger(object):
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(msg)

def download_video(url, download_id):
    def progress_hook(d):
        if d['status'] == 'downloading':
            try:
                percent = d.get('_percent_str', '0%').strip()
                speed = d.get('_speed_str', '0KiB/s').strip()
                eta = d.get('_eta_str', '00:00').strip()
                
                # clean up ANSI escape codes
                percent = ansi_escape.sub('', percent)
                speed = ansi_escape.sub('', speed)
                eta = ansi_escape.sub('', eta)

                downloads[download_id] = {
                    'status': 'downloading',
                    'percent': percent,
                    'speed': speed,
                    'eta': eta,
                    'title': d.get('info_dict', {}).get('title', 'Video')
                }
            except Exception as e:
                pass
        elif d['status'] == 'finished':
            downloads[download_id] = {
                'status': 'finished',
                'percent': '100%',
                'speed': '0',
                'eta': '00:00',
                'title': d.get('info_dict', {}).get('title', 'Video')
            }

    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
        'extractor_args': {
            'youtube': ['player_client=android,web']
        },
    }

    try:
        downloads[download_id] = {'status': 'starting', 'percent': '0%', 'speed': '0', 'eta': '...', 'title': 'Preparing...'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        downloads[download_id] = {'status': 'error', 'error': str(e)}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    download_id = str(uuid.uuid4())
    thread = threading.Thread(target=download_video, args=(url, download_id))
    thread.start()
    
    return jsonify({'download_id': download_id})

@app.route('/api/progress/<download_id>')
def get_progress(download_id):
    info = downloads.get(download_id, {'status': 'not_found'})
    return jsonify(info)

if __name__ == '__main__':
    app.run(port=5000)
