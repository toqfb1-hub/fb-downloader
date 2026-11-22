from flask import Flask, request, jsonify, send_file
import yt_dlp
import os, uuid, glob, time

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup():
    now = time.time()
    for f in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        if os.path.getmtime(f) < now - 600:
            try: os.remove(f)
            except: pass

@app.route("/api/info", methods=["POST"])
def info():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "Please paste a Facebook video link 🔗"}), 400
    try:
        ydl_opts = {"quiet": True, "skip_download": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        formats, seen = [], set()
        for f in info.get("formats", []):
            if f.get("vcodec") == "none": continue
            height = f.get("height") or 0
            ext = f.get("ext", "mp4")
            label = f"{height}p" if height else "video"
            key = (label, ext)
            if key in seen: continue
            seen.add(key)
            formats.append({"format_id": f["format_id"], "label": label, "ext": ext})
        return jsonify({
            "title": info.get("title") or "Facebook Video",
            "formats": formats[:8] or [{"format_id": "best", "label": "Best", "ext": "mp4"}],
        })
    except Exception:
        return jsonify({"error": "Could not fetch video 😕"}), 400

@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    format_id = (data or {}).get("format_id", "best")
    if not url: return jsonify({"error": "Missing URL"}), 400
    cleanup()
    file_id = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")
    try:
        ydl_opts = {
            "outtmpl": outtmpl,
            "format": format_id if format_id != "best" else "best[ext=mp4]/best",
            "quiet": True, "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_id}.*"))
        return send_file(files[0], as_attachment=True, download_name=os.path.basename(files[0]))
    except Exception as e:
        return jsonify({"error": f"Download error: {str(e)[:120]}"}), 500

@app.route("/")
def index():
    return "Server is live!"
