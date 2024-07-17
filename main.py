import json
from dotenv import load_dotenv
import os
import base64
from requests import post, get
import csv

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

def get_token():
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    
    if result.status_code != 200:
        print("Error:", result.content.decode("utf-8"))
        raise Exception("Failed to retrieve token")

    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def search_for_artist(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={artist_name}&type=artist&limit=1"
     
    query_url = url + query
    result = get(query_url, headers=headers)
    
    if result.status_code != 200:
        print("Error:", result.content.decode("utf-8"))
        raise Exception("Failed to search for artist")

    json_result = json.loads(result.content)
    return json_result["artists"]["items"][0]

def get_artist_top_tracks(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    
    if result.status_code != 200:
        print("Error:", result.content.decode("utf-8"))
        raise Exception("Failed to get top tracks")

    json_result = json.loads(result.content)
    return json_result["tracks"]

def get_related_artists(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/related-artists"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    
    if result.status_code != 200:
        print("Error:", result.content.decode("utf-8"))
        raise Exception("Failed to get related artists")

    json_result = json.loads(result.content)
    return json_result["artists"]

def get_audio_features(token, track_ids):
    url = f"https://api.spotify.com/v1/audio-features?ids={','.join(track_ids)}"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    
    if result.status_code != 200:
        print("Error:", result.content.decode("utf-8"))
        raise Exception("Failed to get audio features")

    json_result = json.loads(result.content)
    return json_result["audio_features"]

def collect_data(artist_names):
    token = get_token()
    all_data = []
    processed_artists = set()
    for artist_name in artist_names:
        try:
            artist = search_for_artist(token, artist_name)
            if artist["id"] in processed_artists:
                continue
            processed_artists.add(artist["id"])
            top_tracks = get_artist_top_tracks(token, artist["id"])
            track_ids = [track["id"] for track in top_tracks]
            audio_features = get_audio_features(token, track_ids)
            
            for i, track in enumerate(top_tracks):
                data = {
                    "artist_name": artist["name"],
                    "track_name": track["name"],
                    "track_id": track["id"],
                    "audio_features": audio_features[i]
                }
                all_data.append(data)
            
            related_artists = get_related_artists(token, artist["id"])
            for related_artist in related_artists:
                if related_artist["id"] not in processed_artists:
                    processed_artists.add(related_artist["id"])
                    top_tracks = get_artist_top_tracks(token, related_artist["id"])
                    track_ids = [track["id"] for track in top_tracks]
                    audio_features = get_audio_features(token, track_ids)
                    
                    for i, track in enumerate(top_tracks):
                        data = {
                            "artist_name": related_artist["name"],
                            "track_name": track["name"],
                            "track_id": track["id"],
                            "audio_features": audio_features[i]
                        }
                        all_data.append(data)
        except Exception as e:
            print(f"Error collecting data for {artist_name}: {e}")
    return all_data

def save_to_csv(data, filename="song_new.csv"):
    keys = data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)

def main():
    artist_names = ["ACDC", "The Beatles", "Eminem", "Taylor Swift","Drake", "Travis Scott", "Future"]  # Add more artist names as needed
    data = collect_data(artist_names)
    print(json.dumps(data, indent=4))
    save_to_csv(data)

if __name__ == "__main__":
    main()
