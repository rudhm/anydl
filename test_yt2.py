import yt_dlp

video_url = "https://www.youtube.com/watch?v=ktdbUIZKeSE"

ydl_opts = {
    'quiet': False,
    'format': 'best', # Just 'best' instead of 'bestvideo+bestaudio'
    'extractor_args': {
        'youtube': ['player_client=android,web']
    }
}

print(f"\n--- Testing format='best' ---")
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        print(f"SUCCESS!")
except Exception as e:
    print(f"FAILED: {e}")
