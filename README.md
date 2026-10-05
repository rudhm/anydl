# AnyDL backend

The Vercel site is only the frontend. The downloader runs as two persistent Docker
services on the Oracle VM: an API and a worker. SQLite stores job state and the
mounted data directory stores completed files.

## Oracle VM deployment

Install Docker and Compose on the VM, then run:

```sh
sudo mkdir -p /srv/anydl/downloads
sudo chown -R "$USER":"$USER" /srv/anydl
# Copy an authenticated Netscape-format cookies file to:
# /srv/anydl/instagram-cookies.txt
cp .env.example .env
# Set PUBLIC_ORIGIN to the Vercel site's exact origin.
docker compose up -d --build
```

Expose port `5001` through the VM firewall and reverse proxy it behind HTTPS,
for example at `https://api.example.com`.

After the API URL is available, set `window.ANYDL_API_BASE` before the application
script in `index.html` to that URL and redeploy the frontend:

```html
<script>window.ANYDL_API_BASE = 'https://api.example.com';</script>
```

The worker polls SQLite for queued jobs, updates progress durably, and writes
finished files to `/srv/anydl/downloads`.

## Instagram authentication

Instagram may require an authenticated session even for apparently public reels.
Export cookies for an Instagram account you control in Netscape format and copy
the file to `/srv/anydl/instagram-cookies.txt` on the VM. Do not commit the file
or paste its contents into chat. The worker mounts it read-only and passes it to
yt-dlp only for downloads running on the VM.

Cookies expire or may be revoked. If Instagram starts returning login or
rate-limit errors, export a fresh cookies file and restart the worker:

```sh
docker compose restart anydl-worker
```
