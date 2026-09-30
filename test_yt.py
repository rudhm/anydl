import yt_dlp

video_url = "https://www.youtube.com/watch?v=ktdbUIZKeSE"

configs = [
    ("Default", {}),
    ("Client=android,web", {"extractor_args": {"youtube": ["player_client=android,web"]}}),
    ("Client=tv", {"extractor_args": {"youtube": ["player_client=tv"]}}),
    ("Client=tv,web", {"extractor_args": {"youtube": ["player_client=tv,web"]}}),
    ("Client=ios", {"extractor_args": {"youtube": ["player_client=ios"]}}),
    ("Cookies=Safari", {"cookiesfrombrowser": ("safari",)}),
    ("Cookies=Chrome", {"cookiesfrombrowser": ("chrome",)}),
]

for name, opts in configs:
    print(f"\n--- Testing {name} ---")
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
    }
    ydl_opts.update(opts)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            print(f"SUCCESS: Found video '{info.get('title')}'")
    except Exception as e:
        print(f"FAILED: {e}")
