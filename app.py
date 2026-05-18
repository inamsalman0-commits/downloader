import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

# CORS: Apne Blogger ka address yahan zaroor sahi likhein
CORS(app, origins=[
    "https://YOUR-BLOG.blogspot.com", 
    "http://127.0.0.1:5500",
    "http://localhost:5000"
])

def format_bytes(size):
    if not size: return "Size N/A"
    for unit in ['Bytes', 'KiB', 'MiB', 'GiB']:
        if size < 1024.0: return f"{size:.1f} {unit}"
        size /= 1024.0

@app.route('/')
def index():
    return jsonify({"status": "Vercel Premium Server is Live", "bypass": "OAuth Native Enabled"})

@app.route('/fetch', methods=['POST'])
def fetch_qualities():
    data = request.get_json() or {}
    video_url = data.get('url')
    
    if not video_url:
        return jsonify({'error': 'URL khali hai!'})

    # 🔥 ULTIMATE BYPASS FOR CLOUD BANS (No Cookies Required)
    # Android Embedded aur TV clients use karne se YouTube signature login nahi mangta
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {
                'client': ['android_embedded', 'tv_embedded'],
                'skip': ['dash', 'hls'] # Direct MP4 streams ko target karne ke liye
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Android 14; Mobile; rv:124.0) Gecko/124.0 Firefox/124.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            formats_raw = info_dict.get('formats', [])
            title = info_dict.get('title', 'video')
            
        ui_formats = []
        seen_res = set()
        
        for fmt in formats_raw:
            # Sirf woh links nikalna jo direct downloadable video streams hain
            if fmt.get('ext') == 'mp4' and fmt.get('height') and fmt.get('url'):
                height = fmt.get('height')
                if height in seen_res: continue
                seen_res.add(height)
                
                filesize = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                size_str = format_bytes(filesize)
                
                ui_formats.append({
                    'format_id': fmt['format_id'],
                    'quality': f"{height}p",
                    'ext': 'mp4',
                    'size': size_str,
                    'type': 'video',
                    'url': fmt['url'] # Pure Google Video Stream Link
                })
                
        # High Quality Audio M4A/MP3 Stream Extraction
        for fmt in formats_raw:
            if fmt.get('vcodec') == 'none' and fmt.get('url') and (fmt.get('ext') == 'm4a' or fmt.get('ext') == 'mp3'):
                ui_formats.append({
                    'format_id': 'bestaudio',
                    'quality': 'Audio Track (High MP3/M4A)',
                    'ext': 'mp3',
                    'size': 'Direct Stream',
                    'type': 'audio',
                    'url': fmt['url']
                })
                break
        
        video_items = [f for f in ui_formats if f['type'] == 'video']
        video_items.sort(key=lambda x: int(x['quality'].replace('p','')), reverse=True)
        
        audio_items = [f for f in ui_formats if f['type'] == 'audio']
        
        return jsonify({
            'title': title,
            'formats': video_items + audio_items
        })
        
    except Exception as e:
        return jsonify({'error': f"Details nikalne mein masla aaya: {str(e)}"})

app.debug = True