import os
import sqlite3
import subprocess
import time

import imageio_ffmpeg
import yt_dlp

from app import (
    DOWNLOAD_DIR,
    SUPPORTED_FORMATS,
    cleanup_download_files,
    database,
    update_job,
)

POLL_INTERVAL = float(os.environ.get('WORKER_POLL_INTERVAL', '2'))
COOKIE_FILE = os.environ.get('YTDLP_COOKIE_FILE', '').strip()
ANSI_ESCAPE = __import__('re').compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class MyLogger:
    def debug(self, message):
        pass

    def warning(self, message):
        print(message)

    def error(self, message):
        print(message)


def claim_job():
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        updated = connection.execute(
            "UPDATE jobs SET status = 'starting' WHERE id = ? AND status = 'queued'",
            (row['id'],),
        ).rowcount
        return row if updated else None


def ffmpeg_path():
    return imageio_ffmpeg.get_ffmpeg_exe()


def process_job(job):
    job_id = job['id']
    output_format = job['output_format']
    output_base = os.path.join(DOWNLOAD_DIR, job_id)

    def progress_hook(data):
        if data.get('status') != 'downloading':
            return
        percent = ANSI_ESCAPE.sub('', str(data.get('_percent_str', '0%')).strip())
        speed = ANSI_ESCAPE.sub('', str(data.get('_speed_str', '0KiB/s')).strip())
        eta = ANSI_ESCAPE.sub('', str(data.get('_eta_str', '00:00')).strip())
        title = data.get('info_dict', {}).get('title', 'Downloading...')
        update_job(job_id, status='downloading', percent=percent, speed=speed, eta=eta, title=title)

    options = {
        'outtmpl': output_base + '.%(ext)s',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    if COOKIE_FILE:
        if not os.path.isfile(COOKIE_FILE):
            update_job(job_id, status='error', error='Configured yt-dlp cookie file does not exist.', percent='0%')
            return
        options['cookiefile'] = COOKIE_FILE
    if output_format == 'srt':
        options.update({
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en.*'],
            'subtitlesformat': 'srt/best',
        })

    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([job['url']])

        if output_format == 'srt':
            candidates = [
                name for name in os.listdir(DOWNLOAD_DIR)
                if name.startswith(job_id + '.') and name.endswith('.srt')
            ]
            if not candidates:
                raise RuntimeError('No English subtitles are available for this video.')
            source = os.path.join(DOWNLOAD_DIR, candidates[0])
            target = output_base + '.srt'
            if source != target:
                os.replace(source, target)
        else:
            candidates = [
                name for name in os.listdir(DOWNLOAD_DIR)
                if name.startswith(job_id + '.') and not name.endswith('.part')
            ]
            if not candidates:
                raise RuntimeError('The downloaded media file could not be found.')
            source = os.path.join(DOWNLOAD_DIR, candidates[0])
            target = output_base + '.' + output_format
            update_job(job_id, status='converting', percent='99%', speed='0', eta='...')
            subprocess.run(
                [ffmpeg_path(), '-y', '-i', source, target],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            os.remove(source)

        update_job(
            job_id,
            status='finished',
            percent='100%',
            speed='0',
            eta='00:00',
            filename=os.path.basename(target),
        )
    except Exception as error:
        cleanup_download_files(job_id)
        update_job(job_id, status='error', error=str(error), percent='0%')


def run():
    while True:
        job = claim_job()
        if job is None:
            time.sleep(POLL_INTERVAL)
            continue
        process_job(job)


if __name__ == '__main__':
    run()
