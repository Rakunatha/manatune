"""
Provenance Tracker — minimal backend
Three things this serves:
  1. GET  /api/apps     -> directory of AI apps/platforms to browse
  2. GET  /api/events   -> log of created / downloaded / distributed items
     POST /api/events   -> add a new event to that log
  3. GET  /api/analyze  -> stats + an AI-written analysis of the event log
                           (stats are always computed; the written analysis
                           needs a Groq API key)

Run:
  pip install -r requirements.txt
  export GROQ_API_KEY=your_key_here   # optional, enables AI insights
  python app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, jsonify, request, render_template
import uuid
import datetime
import os
import requests
from collections import Counter

app = Flask(__name__, template_folder=".")

# ---- Groq (https://console.groq.com) config for the AI-written analysis ----
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

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


def _compute_stats():
    """Pure number-crunching over EVENTS — no AI involved. This always
    works, even with no GROQ_API_KEY set."""
    total = len(EVENTS)
    by_action = Counter(e["action"] for e in EVENTS)
    by_tool = Counter(e["tool"] for e in EVENTS)
    by_user = Counter(e["user"] for e in EVENTS)

    return {
        "total": total,
        "by_action": dict(by_action),
        "by_tool": by_tool.most_common(),
        "by_user": by_user.most_common(),
        "top_tool": by_tool.most_common(1)[0][0] if by_tool else None,
        "top_user": by_user.most_common(1)[0][0] if by_user else None,
        "created": by_action.get("Created", 0),
        "downloaded": by_action.get("Downloaded", 0),
        "distributed": by_action.get("Distributed", 0),
        "visited": by_action.get("Visited", 0),
    }


def _build_prompt(stats):
    lines = [
        "You are a provenance analyst reviewing a log of AI-generated content "
        "activity: what was created, downloaded, and distributed, with which "
        "tool, by which user.",
        "",
        f"Total events: {stats['total']}",
        f"Created: {stats['created']}  Downloaded: {stats['downloaded']}  "
        f"Distributed: {stats['distributed']}  Visited/opened: {stats['visited']}",
        "",
        "Event counts by tool: " + ", ".join(f"{t}={c}" for t, c in stats["by_tool"]) or "(none)",
        "Event counts by user: " + ", ".join(f"{u}={c}" for u, c in stats["by_user"]) or "(none)",
        "",
        "Recent raw events (newest first, up to 40):",
    ]
    for e in EVENTS[:40]:
        lines.append(
            f"- [{e['timestamp']}] {e['user']} {e['action'].lower()} "
            f"'{e['item']}' using {e['tool']}"
        )

    lines += [
        "",
        "Write a concise but in-depth analysis (use short headers and bullet "
        "points) covering:",
        "1. Overall activity pattern — what's being created vs. downloaded vs. distributed.",
        "2. Which tools dominate, and for which kind of action.",
        "3. Who is most active, and any concentration worth flagging.",
        "4. Provenance/traceability observations — e.g. items that were "
        "distributed without a matching 'created' entry, or tools used only "
        "for distribution rather than creation.",
        "5. Two or three concrete recommendations for better tracking or "
        "governance going forward.",
        "Be specific and reference the actual numbers/tools/users above. "
        "Do not invent data that isn't in the log.",
    ]
    return "\n".join(lines)


@app.route("/api/analyze")
def analyze():
    stats = _compute_stats()

    # Stats are free and always computed. The AI-written analysis calls
    # Groq, so it only runs when explicitly requested (?ai=1) — e.g. when
    # the user clicks "Generate insights" — not on every page load.
    want_ai = request.args.get("ai") == "1"

    if stats["total"] == 0:
        return jsonify({
            "stats": stats,
            "insights": None,
            "note": "No events logged yet — log some activity on the Track "
                    "page first.",
        })

    if not want_ai:
        return jsonify({"stats": stats, "insights": None, "note": None})

    if not GROQ_API_KEY:
        return jsonify({
            "stats": stats,
            "insights": None,
            "note": "Set the GROQ_API_KEY environment variable to enable "
                    "AI-written insights (get a key at console.groq.com). "
                    "Stats below are computed either way.",
        })

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "user", "content": _build_prompt(stats)},
                ],
                "temperature": 0.4,
                "max_tokens": 900,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        insights = data["choices"][0]["message"]["content"]
        return jsonify({"stats": stats, "insights": insights, "note": None})

    except requests.exceptions.RequestException as e:
        return jsonify({
            "stats": stats,
            "insights": None,
            "note": f"Groq API request failed: {e}",
        }), 502
    except (KeyError, IndexError):
        return jsonify({
            "stats": stats,
            "insights": None,
            "note": "Groq API returned an unexpected response format.",
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
