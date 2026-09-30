import urllib.request
import json

api_url = "https://api.cobalt.tools/"
data = json.dumps({
    "url": "https://www.youtube.com/watch?v=ktdbUIZKeSE",
    "videoQuality": "1080"
}).encode('utf-8')

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
    else:
        print(e)
