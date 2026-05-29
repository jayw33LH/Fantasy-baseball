import base64
import json
import os
import re

import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from luck_analyzer import find_player, get_luck_data

load_dotenv()

app = Flask(__name__)
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic(api_key=key)
    return _client


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/luck-data")
def luck_data():
    force = request.args.get("refresh", "").lower() == "true"
    return jsonify(get_luck_data(force_refresh=force))


@app.route("/api/analyze-screenshot", methods=["POST"])
def analyze_screenshot():
    try:
        client = get_client()
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    img_file = request.files["image"]
    img_bytes = img_file.read()
    if not img_bytes:
        return jsonify({"error": "Empty image"}), 400

    img_b64 = base64.standard_b64encode(img_bytes).decode()
    media_type = img_file.content_type or "image/png"
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        media_type = "image/png"

    context = request.form.get("context", "my fantasy roster")

    # --- Step 1: Extract player names via Claude Vision ---
    extract = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": img_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"This is a screenshot of {context} from a fantasy baseball app.\n\n"
                            "Extract ALL MLB player names visible. Return ONLY a JSON array of names "
                            "as they appear, e.g.: [\"Mike Trout\", \"Shohei Ohtani\"]\n\n"
                            "Return only the JSON array, nothing else."
                        ),
                    },
                ],
            }
        ],
    )

    raw = extract.content[0].text.strip()
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    try:
        player_names = json.loads(match.group()) if match else []
    except Exception:
        player_names = []

    if not player_names:
        return jsonify(
            {
                "success": False,
                "message": "No player names found in screenshot",
                "raw_response": raw,
            }
        )

    # --- Step 2: Cross-reference with luck data ---
    luck = get_luck_data()
    batters = luck.get("batters", [])
    pitchers = luck.get("pitchers", [])

    matched = []
    for name in player_names:
        b = find_player(name, batters)
        p = find_player(name, pitchers)
        hit = b or p
        ptype = "batter" if b else ("pitcher" if p else "unknown")

        if hit:
            score = hit["luck_score"]
            threshold = 0.015 if ptype == "batter" else 0.25
            matched.append(
                {
                    "name": name,
                    "matched_name": hit["name"],
                    "type": ptype,
                    "luck_score": score,
                    "lucky": score > threshold,
                    "unlucky": score < -threshold,
                    "stats": hit,
                }
            )
        else:
            matched.append(
                {
                    "name": name,
                    "matched_name": None,
                    "type": "unknown",
                    "luck_score": None,
                    "stats": None,
                }
            )

    # --- Step 3: Generate fantasy analysis ---
    analysis = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a fantasy baseball analyst specializing in sabermetric luck analysis.\n\n"
                    f"Context: {context}\n\n"
                    "Player luck data:\n"
                    + json.dumps(matched, indent=2)
                    + "\n\n"
                    "Luck score guide:\n"
                    "• Batters: luck = wOBA − xwOBA. Positive = getting MORE than contact quality deserves (lucky, expect regression). Negative = getting LESS (unlucky, expect improvement).\n"
                    "• Pitchers: luck = xERA − ERA. Positive = ERA better than underlying quality (lucky, expect regression). Negative = ERA worse than deserves (unlucky, expect improvement).\n\n"
                    "Provide:\n"
                    "1. Lucky players to SELL HIGH or fade (bold the names)\n"
                    "2. Unlucky players to BUY LOW or target (bold the names)\n"
                    "3. Specific actionable fantasy advice (start/sit, add/drop, trade)\n\n"
                    "Be concise and direct. Use bullet points."
                ),
            }
        ],
    )

    return jsonify(
        {
            "success": True,
            "players_found": player_names,
            "matched_players": matched,
            "analysis": analysis.content[0].text,
            "context": context,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
