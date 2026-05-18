import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

# CORS setup: Apne Blogger ka URL yahan zaroor sahi se likhein
CORS(app, origins=[
    "https://YOUR-BLOG.blogspot.com", # <--- Isko apne blog ke link se badlein
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
    return jsonify({"status": "Vercel API Server is live", "bypass": "Enabled"})

@app.route('/fetch', methods=['POST'])
def fetch_qualities():
    data = request.get_json() or {}
    video_url = data.get('url')
    
    if not video_url:
        return jsonify({'error': 'URL khali hai!'})

    # 🔥 Bypassing "Sign in to confirm you're not a bot" Error
    # Hum yt-dlp ko keh rahe hain ke woh web browser ki bajaye YouTube Mobile Android/iOS client ban kar request kare
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {
                'client': ['android', 'ios', 'web_embedded']
            }
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
                    'url': fmt['url']
                })
                
        # Best Audio Option
        for fmt in formats_raw:
            if fmt.get('vcodec') == 'none' and fmt.get('url'):
                ui_formats.append({
                    'format_id': 'bestaudio',
                    'quality': 'MP3 Audio (High Quality)',
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