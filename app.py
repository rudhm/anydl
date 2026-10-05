from flask import Flask, jsonify, request, send_from_directory
import os
import re
import sqlite3
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', os.path.join(BASE_DIR, 'downloads'))
DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'anydl.sqlite3'))
PUBLIC_ORIGIN = os.environ.get('PUBLIC_ORIGIN', '*')

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
app = Flask(__name__, static_folder=BASE_DIR)
SUPPORTED_FORMATS = {
    'mp4', 'webm', 'mkv', 'mov', 'avi', 'gif',
    'mp3', 'm4a', 'wav', 'flac', 'ogg', 'srt'
}
DOWNLOAD_ID_PATTERN = re.compile(r'^[0-9a-f-]{36}$')


def database():
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with database() as connection:
        connection.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                output_format TEXT NOT NULL,
                status TEXT NOT NULL,
                percent TEXT NOT NULL DEFAULT '0%',
                speed TEXT NOT NULL DEFAULT '0',
                eta TEXT NOT NULL DEFAULT '...',
                title TEXT NOT NULL DEFAULT 'Preparing...',
                filename TEXT,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')


def job_response(row):
    response = {
        'status': row['status'],
        'percent': row['percent'],
        'speed': row['speed'],
        'eta': row['eta'],
        'title': row['title'],
    }
    if row['filename']:
        response['filename'] = row['filename']
    if row['error']:
        response['error'] = row['error']
    return response


def update_job(job_id, **values):
    assignments = ', '.join(f'{key} = ?' for key in values)
    with database() as connection:
        connection.execute(
            f'UPDATE jobs SET {assignments} WHERE id = ?',
            (*values.values(), job_id),
        )


def cleanup_download_files(job_id):
    prefix = job_id + '.'
    for name in os.listdir(DOWNLOAD_DIR):
        if name.startswith(prefix):
            path = os.path.join(DOWNLOAD_DIR, name)
            if os.path.isfile(path):
                os.remove(path)


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = PUBLIC_ORIGIN
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/api/download', methods=['POST', 'OPTIONS'])
def start_download():
    if request.method == 'OPTIONS':
        return '', 204
    data = request.get_json(silent=True) or {}
    url = data.get('url')
    output_format = data.get('format', 'mp4')
    if not isinstance(url, str) or not url.strip():
        return jsonify({'error': 'No URL provided'}), 400
    if not isinstance(output_format, str) or output_format.lower() not in SUPPORTED_FORMATS:
        return jsonify({'error': 'Unsupported output format'}), 400

    job_id = str(uuid.uuid4())
    with database() as connection:
        connection.execute(
            'INSERT INTO jobs (id, url, output_format, status) VALUES (?, ?, ?, ?)',
            (job_id, url.strip(), output_format.lower(), 'queued'),
        )
    return jsonify({'download_id': job_id}), 202


@app.route('/api/progress/<job_id>')
def get_progress(job_id):
    if not DOWNLOAD_ID_PATTERN.fullmatch(job_id):
        return jsonify({'status': 'not_found'}), 404
    with database() as connection:
        row = connection.execute(
            'SELECT status, percent, speed, eta, title, filename, error '
            'FROM jobs WHERE id = ?',
            (job_id,),
        ).fetchone()
    if row is None:
        return jsonify({'status': 'not_found'}), 404
    return jsonify(job_response(row))


@app.route('/download/<filename>')
def serve_file(filename):
    if not re.fullmatch(r'[0-9a-f-]{36}\.[a-z0-9]+', filename):
        return jsonify({'error': 'Invalid file name'}), 404
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


initialize_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5001')))
