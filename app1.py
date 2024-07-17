import os
import json
from flask import Flask, request, render_template, jsonify
import pandas as pd
import ast
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = "http://localhost:5000/callback"

app = Flask(__name__)

# Initialize Spotipy with user authorization
sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope="user-library-read")

user_library_combined_df = pd.DataFrame()  # Global variable to store user library combined DataFrame
X_user_library_scaled = None  # Global variable to store scaled user library features
fit_columns = []  # Global variable to store columns used during fitting

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_spotify_auth_url():
    auth_url = sp_oauth.get_authorize_url()
    return auth_url

def get_spotify_token(auth_code):
    token_info = sp_oauth.get_access_token(auth_code)
    return token_info['access_token']

def get_user_saved_tracks(sp):
    results = sp.current_user_saved_tracks(limit=50)
    saved_tracks = []
    while results:
        for item in results['items']:
            track = item['track']
            saved_tracks.append(track)
        if results['next']:
            results = sp.next(results)
        else:
            results = None

    return saved_tracks

def get_token():
    with open("token.json", "r") as token_file:
        token_data = json.load(token_file)
    return token_data["access_token"]

@app.route('/')
def index():
    try:
        auth_url = get_spotify_auth_url()
        print(f"Auth URL: {auth_url}")  # Print the auth URL for debugging
        return render_template('index.html', auth_url=auth_url)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        print(f"Error in index route: {e}")  # Print error message for debugging
        return "An error occurred in the index route."

@app.route('/callback')
def callback():
    global user_library_combined_df, X_user_library_scaled, fit_columns

    print("Callback route called")  # Early debug statement

    try:
        auth_code = request.args.get('code')
        print(f"Auth Code: {auth_code}")  # Print auth code for debugging
        token = get_spotify_token(auth_code)
        print(f"Token: {token}")  # Print token for debugging
        with open("token.json", "w") as token_file:
            json.dump({"access_token": token}, token_file)
        sp = Spotify(auth=token)
        saved_tracks = get_user_saved_tracks(sp)
        print(f"Saved Tracks: {saved_tracks}")  # Print saved tracks for debugging
        
        if saved_tracks is None:
            logger.error("No saved tracks found.")
            print("No saved tracks found.")  # Print error message for debugging
            return "No saved tracks found."

        # Prepare user library DataFrame
        user_library_df = pd.DataFrame(saved_tracks)
        logger.info(f"User library DataFrame columns: {user_library_df.columns}")
        print(f"User library DataFrame columns: {user_library_df.columns}")  # Print columns for debugging

        user_library_df['audio_features'] = user_library_df['id'].apply(lambda x: sp.audio_features(x)[0] if x is not None else {})
        user_library_audio_features_df = pd.json_normalize(user_library_df['audio_features'])
        user_library_combined_df = pd.concat([user_library_df.drop(columns=['audio_features']), user_library_audio_features_df], axis=1)
        
        # Remove duplicate columns
        user_library_combined_df = user_library_combined_df.loc[:,~user_library_combined_df.columns.duplicated()]

        # Ensure artist_name and track_name are included
        user_library_combined_df['artist_name'] = user_library_df['artists'].apply(lambda x: x[0]['name'] if len(x) > 0 else '')
        user_library_combined_df['track_name'] = user_library_df['name']

        # Print column names for inspection
        logger.info(f"user_library_combined_df columns: {user_library_combined_df.columns}")
        print(f"user_library_combined_df columns: {user_library_combined_df.columns}")  # Print columns for debugging
        
        # Define columns used during fitting
        fit_columns = list(X.columns)
        print(f"Fit columns: {fit_columns}")  # Print fit columns for debugging
        
        # Ensure consistent column order
        user_library_combined_df = user_library_combined_df[fit_columns + ['artist_name', 'track_name']]
        print(f"User library combined DataFrame after reordering: {user_library_combined_df.columns}")  # Print reordered columns for debugging

        # Scale the data
        X_user_library = user_library_combined_df[fit_columns]
        X_user_library_scaled = scaler.transform(X_user_library)

        return render_template('chat.html')
    except Exception as e:
        logger.error(f"Error in callback route: {e}")
        print(f"Error in callback route: {e}")  # Print error message for debugging
        return "An error occurred in the callback route."

@app.route('/chat', methods=['POST'])
def chat():
    global user_library_combined_df, X_user_library_scaled, fit_columns

    try:
        user_message = request.json.get('message')
        token = get_token()
        sp = Spotify(auth=token)
        
        # Check if user is asking for a recommendation
        if 'recommend' in user_message.lower():
            song_query = user_message.lower().replace('recommend', '').strip()
            if not song_query:
                return jsonify({"message": "Please specify a song name after 'recommend'."})

            # Search for the song based on user input
            song = sp.search(q=song_query, type='track', limit=1)['tracks']['items'][0]
            song_features = sp.audio_features(song['id'])[0]
            song_features_df = pd.DataFrame([song_features])
            song_features_df = song_features_df[fit_columns]  # Ensure columns match the order during fit
            song_features_scaled = scaler.transform(song_features_df)

            # Perform similarity matching against user library
            recommended_songs = recommend_songs(song_features_scaled[0], X_user_library_scaled, user_library_combined_df, n=10)

            response_message = "Here are some songs you might like:<br>" + "<br>".join([f"{song['artist_name']} - {song['track_name']}" for _, song in recommended_songs.iterrows()])
        else:
            response_message = "I can help you find song recommendations. Just type 'recommend' followed by a song name."

        return jsonify({"message": response_message})
    except Exception as e:
        logger.error(f"Error in chat route: {e}")
        print(f"Error in chat route: {e}")  # Print error message for debugging
        return jsonify({"message": "An error occurred while processing your request."})

# Data preparation functions from Jupyter Notebook
def parse_audio_features(audio_features_str):
    return ast.literal_eval(audio_features_str)

# Load and preprocess initial data
df = pd.read_csv('song_new.csv')
df['audio_features'] = df['audio_features'].apply(parse_audio_features)
audio_features_df = pd.json_normalize(df['audio_features'])
df_combined = pd.concat([df.drop(columns=['audio_features']), audio_features_df], axis=1)
X = df_combined.drop(columns=['artist_name', 'track_name', 'track_id', 'id', 'uri', 'track_href', 'analysis_url', 'type'])
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_scaled = pd.DataFrame(X_scaled, columns=X.columns)

def find_similar_songs(input_song_features, all_songs_features, n=10):
    similarities = cosine_similarity([input_song_features], all_songs_features)
    similar_indices = similarities.argsort()[0][-n-1:-1]
    return similar_indices

def recommend_songs(song_features, X_scaled, df, n=10):
    similar_songs_indices = find_similar_songs(song_features, X_scaled, n)
    similar_songs = df.iloc[similar_songs_indices]
    return similar_songs[['artist_name', 'track_name']]

if __name__ == "__main__":
    app.run(port=5000, debug=True)
