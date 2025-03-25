import requests
import pandas as pd
import time
import os

# Configuration
client_id = "lbcktr452fhxdeaotmvp1hh9maewqu"  # Your Client ID
token = "9vzif3ufee5vhq1io3zo1l2gh78ks1"  # Your OAuth Token
input_filename = "top_1000_twitch.csv"  # Input CSV file containing streamer names
output_filename = "streamer_details.csv"  # Output CSV file for saving data
image_folder = "streamer_images"  # Folder to store images

# Create the image folder if it doesn't exist
os.makedirs(image_folder, exist_ok=True)

# Check if input file exists
if not os.path.exists(input_filename):
    print(f"❌ Error: Input file '{input_filename}' not found!")
    exit()

print(f"🔍 Reading input file '{input_filename}'...")
streamers = pd.read_csv(input_filename)
print(f"✅ Successfully read {len(streamers)} streamers from the input file.")

# Prepare headers for Twitch API requests
headers = {
    "Client-ID": client_id,
    "Authorization": f"Bearer {token}"
}

# Function to get streamer info from the Twitch API
def get_streamer_info(username):
    url = f"https://api.twitch.tv/helix/users?login={username}"
    try:
        print(f"🌐 Sending request for streamer: {username}")
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        print(f"✅ Success! Status Code: {response.status_code}")

        data = response.json()
        if "data" in data and data["data"]:
            return data["data"][0]
        else:
            print(f"⚠️ No data found for streamer: {username}")
    except requests.RequestException as e:
        print(f"❌ Error retrieving {username}: {e}")
    return None

# Function to download profile image
def download_image(url, filename):
    try:
        print(f"🖼️ Downloading image from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filename, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"✅ Image saved as {filename}")
    except requests.RequestException as e:
        print(f"❌ Error downloading image: {e}")

# Load existing data to avoid re-fetching
def load_existing_data(filename):
    if os.path.exists(filename):
        print(f"📂 Loading existing data from '{filename}'...")
        return pd.read_csv(filename)
    print("🆕 No existing data found. Starting fresh.")
    return pd.DataFrame(columns=["Rank", "Name", "Display Name", "ID", "Description", "Profile Image URL", "View Count", "Image Path"])

# Load existing data to resume if interrupted
existing_data = load_existing_data(output_filename)
processed_names = set(existing_data["Name"])

# Collect streamer data
streamer_data = existing_data.to_dict(orient="records")

for index, row in streamers.iterrows():
    name = row["Name"]

    # Skip already processed streamers
    if name in processed_names:
        print(f"🔁 Skipping already processed streamer: {name}")
        continue

    streamer_info = get_streamer_info(name)

    # Prepare data to be saved to the output CSV
    if streamer_info:
        profile_image_url = streamer_info.get("profile_image_url", "N/A")
        image_path = "N/A"

        # Download profile image if the URL is valid
        if profile_image_url != "N/A":
            image_filename = os.path.join(image_folder, f"{name}.jpg")
            download_image(profile_image_url, image_filename)
            image_path = image_filename

        streamer_data.append({
            "Rank": row["Rank"],
            "Name": name,
            "Display Name": streamer_info.get("display_name", "N/A"),
            "ID": streamer_info.get("id", "N/A"),
            "Description": streamer_info.get("description", "N/A"),
            "Profile Image URL": profile_image_url,
            "View Count": streamer_info.get("view_count", "N/A"),
            "Image Path": image_path
        })
    else:
        streamer_data.append({
            "Rank": row["Rank"],
            "Name": name,
            "Display Name": "N/A",
            "ID": "N/A",
            "Description": "N/A",
            "Profile Image URL": "N/A",
            "View Count": "N/A",
            "Image Path": "N/A"
        })

    # Save the data after every streamer to ensure progress
    output_df = pd.DataFrame(streamer_data)
    output_df.to_csv(output_filename, index=False)
    print(f"💾 Saved data for {name}")

    # Minimal wait to reduce API stress
    time.sleep(0.01)

print(f"✅ Completed processing. Streamer details saved to '{output_filename}'")
