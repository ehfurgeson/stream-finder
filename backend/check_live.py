import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set your Twitch API credentials here:
TWITCH_CLIENT_ID = "z1akr0fhflhovjnzece9n1yj660c3m"
TWITCH_OAUTH_TOKEN = "Bearer m64wu8k92wt72wssy1un793gza4m2b"  # Note: No braces around the token value

def get_live_metrics(streamer_name):
    """
    Checks if the streamer is live and, if so, gets current viewer count and game name.
    Also fetches follower count using the user's ID.
    Returns a dictionary with:
      - is_live (bool)
      - viewer_count (int, if live; else 0)
      - game_name (str)
      - follower_count (int)
    """
    # Twitch API endpoint for live streams
    streams_url = "https://api.twitch.tv/helix/streams"
    streams_params = {"user_login": streamer_name.lower()}
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": TWITCH_OAUTH_TOKEN
    }
    try:
        streams_response = requests.get(streams_url, params=streams_params, headers=headers, timeout=10)
        streams_response.raise_for_status()
        streams_data = streams_response.json()
    except Exception as e:
        print(f"Error checking live status for {streamer_name}: {e}")
        return {"is_live": False, "viewer_count": 0, "game_name": "", "follower_count": 0}

    is_live = len(streams_data.get("data", [])) > 0
    viewer_count = 0
    game_name = ""
    if is_live:
        live_info = streams_data["data"][0]
        viewer_count = live_info.get("viewer_count", 0)
        game_name = live_info.get("game_name", "")
    
    # Get user ID to fetch follower count
    users_url = "https://api.twitch.tv/helix/users"
    users_params = {"login": streamer_name.lower()}
    try:
        users_response = requests.get(users_url, params=users_params, headers=headers, timeout=10)
        users_response.raise_for_status()
        users_data = users_response.json()
        user_id = users_data.get("data", [{}])[0].get("id", "")
    except Exception as e:
        print(f"Error fetching user ID for {streamer_name}: {e}")
        user_id = ""

    follower_count = 0
    if user_id:
        follows_url = "https://api.twitch.tv/helix/users/follows"
        follows_params = {"to_id": user_id, "first": 1}  # 'first' parameter is not actually used for count
        try:
            follows_response = requests.get(follows_url, params=follows_params, headers=headers, timeout=10)
            follows_response.raise_for_status()
            follows_data = follows_response.json()
            follower_count = follows_data.get("total", 0)
        except Exception as e:
            print(f"Error fetching follower count for {streamer_name}: {e}")

    return {
        "is_live": is_live,
        "viewer_count": viewer_count,
        "game_name": game_name,
        "follower_count": follower_count
    }

app = Flask(__name__)
CORS(app)

@app.route("/live-status", methods=["GET"])
def live_status_endpoint():
    streamer = request.args.get("streamer", "")
    if not streamer:
        return jsonify({"error": "No streamer provided"}), 400
    metrics = get_live_metrics(streamer)
    # Return the metrics along with the streamer name.
    return jsonify({"streamer": streamer, **metrics})

if __name__ == "__main__":
    # Run this service on port 5002
    app.run(debug=True, host="0.0.0.0", port=5002)
