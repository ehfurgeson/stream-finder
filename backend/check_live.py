import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set your Twitch credentials here:
TWITCH_CLIENT_ID = "z1akr0fhflhovjnzece9n1yj660c3m"
TWITCH_OAUTH_TOKEN = "Bearer m64wu8k92wt72wssy1un793gza4m2b"

def get_live_status(streamer_name):
    """
    Check if a streamer is currently live on Twitch using the Twitch Helix API.
    Returns True if live, False otherwise.
    """
    url = "https://api.twitch.tv/helix/streams"
    params = {
        "user_login": streamer_name.lower()
    }
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": TWITCH_OAUTH_TOKEN
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"DEBUG: Twitch API response for {streamer_name}: {data}")  # Debug print
        return len(data.get("data", [])) > 0
    except Exception as e:
        print(f"Error checking live status for {streamer_name}: {e}")
        return False


app = Flask(__name__)
CORS(app)

@app.route("/live-status", methods=["GET"])
def live_status_endpoint():
    streamer = request.args.get("streamer", "")
    if not streamer:
        return jsonify({"error": "No streamer provided"}), 400
    status = get_live_status(streamer)
    return jsonify({"streamer": streamer, "is_live": status})

if __name__ == "__main__":
    # Run this service on port 5002
    app.run(debug=True, host="0.0.0.0", port=5002)
