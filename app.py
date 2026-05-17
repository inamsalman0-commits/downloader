"""
YouTube Downloader Backend — Flask + yt-dlp
==========================================
Deploy karein: Render.com, Railway.app, ya VPS pe

Install:
    pip install flask yt-dlp flask-cors

Run:
    python app.py
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import tempfile

app = Flask(__name__)

# ============================================================
# APNA BLOGGER URL YAHAN DAALEIN (ya * sab ke liye allow karo)
# ============================================================
CORS(app, origins=["https://YOUR-BLOG.blogspot.com", "https://YOUR-CUSTOM-DOMAIN.com"])
# Agar test karna ho sab ke liye: CORS(app)
# ============================================================

TEMP_DIR = tempfile.gettempdir()


def ydl_opts_base():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }


@app.route("/")
def home():
    return jsonify({"status": "YT Downloader API chal raha hai ✅"})


@app.route("/info", methods=["POST"])
def get_info():
    """Video ki maloomat aur available formats wapas karo"""
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL nahi mila"}), 400

    try:
        opts = ydl_opts_base()
        opts["skip_download"] = True

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Video formats (mp4 with video stream)
        video_formats = []
        seen_res = set()
        for f in reversed(info.get("formats", [])):
            if (
                f.get("vcodec") != "none"
                and f.get("acodec") != "none"
                and f.get("ext") == "mp4"
            ):
                res = f.get("height")
                if res and res not in seen_res:
                    seen_res.add(res)
                    video_formats.append({
                        "format_id": f["format_id"],
                        "label": f"{res}p",
                        "type": "video",
                        "filesize": f.get("filesize") or f.get("filesize_approx"),
                    })

        # Agar mp4 combined na mile toh best video add karo
        if not video_formats:
            for f in reversed(info.get("formats", [])):
                if f.get("vcodec") != "none":
                    res = f.get("height")
                    if res and res not in seen_res:
                        seen_res.add(res)
                        video_formats.append({
                            "format_id": f["format_id"],
                            "label": f"{res}p",
                            "type": "video",
                            "filesize": f.get("filesize") or f.get("filesize_approx"),
                        })

        # Audio only formats
        audio_formats = []
        seen_abr = set()
        for f in reversed(info.get("formats", [])):
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                abr = int(f.get("abr") or 0)
                if abr and abr not in seen_abr:
                    seen_abr.add(abr)
                    audio_formats.append({
                        "format_id": f["format_id"],
                        "label": f"{abr}kbps",
                        "type": "audio",
                        "filesize": f.get("filesize") or f.get("filesize_approx"),
                    })

        # Sort by quality (high se low)
        video_formats.sort(key=lambda x: int(x["label"].replace("p", "")), reverse=True)
        audio_formats.sort(key=lambda x: int(x["label"].replace("kbps", "")), reverse=True)

        return jsonify({
            "title": info.get("title", "Unknown"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "channel": info.get("channel", ""),
            "formats": video_formats + audio_formats,
        })

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Video nahi mili: {str(e)[:200]}"}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)[:200]}"}), 500


@app.route("/download", methods=["POST"])
def download_video():
    """Selected format download karo aur client ko bhejo"""
    data = request.get_json()
    url = data.get("url", "").strip()
    format_id = data.get("format_id", "").strip()
    media_type = data.get("type", "video")  # 'video' ya 'audio'

    if not url or not format_id:
        return jsonify({"error": "URL ya format_id nahi mila"}), 400

    file_id = str(uuid.uuid4())
    output_path = os.path.join(TEMP_DIR, f"{file_id}.%(ext)s")

    try:
        if media_type == "audio":
            opts = ydl_opts_base()
            opts.update({
                "format": format_id,
                "outtmpl": output_path,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
            ext = "mp3"
        else:
            opts = ydl_opts_base()
            opts.update({
                # Best video+audio merge karo agar alag streams hon
                "format": f"{format_id}+bestaudio[ext=m4a]/{format_id}/best[ext=mp4]",
                "outtmpl": output_path,
                "merge_output_format": "mp4",
            })
            ext = "mp4"

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # File dhundho
        actual_file = None
        for f in os.listdir(TEMP_DIR):
            if f.startswith(file_id):
                actual_file = os.path.join(TEMP_DIR, f)
                break

        if not actual_file or not os.path.exists(actual_file):
            return jsonify({"error": "File nahi bani, FFmpeg check karein"}), 500

        mime = "audio/mpeg" if ext == "mp3" else "video/mp4"

        def remove_after_send(response):
            try:
                os.remove(actual_file)
            except Exception:
                pass
            return response

        response = send_file(
            actual_file,
            mimetype=mime,
            as_attachment=True,
            download_name=f"download.{ext}",
        )
        response.call_on_close(lambda: _cleanup(actual_file))
        return response

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Download fail: {str(e)[:300]}"}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)[:300]}"}), 500


def _cleanup(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
