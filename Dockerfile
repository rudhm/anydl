FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV DOWNLOAD_DIR=/data/downloads
ENV DATABASE_PATH=/data/anydl.sqlite3
RUN mkdir -p /data/downloads

EXPOSE 5001
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "app:app"]
