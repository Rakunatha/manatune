"""
Provenance Tracker — minimal backend
Two things this serves:
  1. GET  /api/apps    -> directory of AI apps/platforms to browse
  2. GET  /api/events  -> log of created / downloaded / distributed items
     POST /api/events  -> add a new event to that log

Run:
  pip install flask
  python app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, jsonify, request, render_template
import uuid
import datetime

app = Flask(__name__, template_folder=".")

# ---- Directory of AI apps & platforms (page 1: Browse) ----
APPS = [
    {"name": "ChatGPT",        "category": "Conversational AI", "blurb": "General-purpose AI chat assistant.",     "url": "https://chat.openai.com/"},
    {"name": "Claude",         "category": "Conversational AI", "blurb": "AI assistant for writing and reasoning.", "url": "https://claude.ai/"},
    {"name": "Midjourney",     "category": "Image Generation",  "blurb": "Text-to-image generation tool.",          "url": "https://www.midjourney.com/"},
    {"name": "DALL\u00b7E",    "category": "Image Generation",  "blurb": "Image generation from text prompts.",     "url": "https://openai.com/dall-e-2"},
    {"name": "GitHub Copilot", "category": "Code Generation",   "blurb": "AI pair programmer for code.",            "url": "https://github.com/features/copilot"},
    {"name": "ElevenLabs",     "category": "Voice Generation",  "blurb": "AI voice and speech synthesis.",          "url": "https://elevenlabs.io/"},
    {"name": "Runway",         "category": "Video Generation",  "blurb": "AI video generation and editing.",        "url": "https://runwayml.com/"},
    {"name": "Notion AI",      "category": "Productivity",      "blurb": "AI writing assistant inside Notion.",     "url": "https://www.notion.so/product/ai"},
]

# ---- In-memory event log (page 2: Track) ----
EVENTS = []  # each: {id, item, tool, user, action, timestamp}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/apps")
def get_apps():
    return jsonify(APPS)


@app.route("/api/events", methods=["GET", "POST"])
def events():
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        event = {
            "id": str(uuid.uuid4())[:8],
            "item": (data.get("item") or "Untitled item").strip(),
            "tool": (data.get("tool") or "Unknown tool").strip(),
            "user": (data.get("user") or "You").strip(),
            "action": data.get("action") or "Created",
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        }
        EVENTS.insert(0, event)
        return jsonify(event), 201

    return jsonify(EVENTS)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
