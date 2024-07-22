import os
import json
import random
import spacy
from flask import Flask, request, render_template, jsonify, session
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import logging
import openai
from flask_session import Session

# Loav environment variables
from dotenv import load_dotenv
load_dotenv()

model_name = os.environ.get("SPACY_MODEL", "en_core_web_sm")

# Load spaCy model
def load_model():
    try:
        nlp = spacy.load(model_name)
        return nlp
    except OSError as e:
        print(f"Model '{model_name}' not found. Downloading...")
        spacy.cli.download(model_name)
        nlp = spacy.load(model_name)
        return nlp
    

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = "http://localhost:5000/callback"
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Initialize Spotipy with user authorization
sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope="user-library-read")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load spaCy model
nlp = load_model()

# Store user preferences and recommendations
user_preferences = {
    "genres": [],
    "liked_songs": []
}

# Track previously recommended songs
previous_recommendations = {
    "genres": {}
}

def get_spotify_auth_url():
    auth_url = sp_oauth.get_authorize_url()
    return auth_url

def get_spotify_token(auth_code):
    token_info = sp_oauth.get_access_token(auth_code)
    return token_info['access_token']

def get_token():
    with open("token.json", "r") as token_file:
        token_data = json.load(token_file)
    return token_data["access_token"]

def ask_openai(question):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except openai.error.OpenAIError as e:
        logger.error(f"Error calling OpenAI API: {e}")
        if isinstance(e, openai.error.RateLimitError):
            return "I'm sorry, but the service is currently experiencing high demand. Please try again later."
        elif isinstance(e, openai.error.InvalidRequestError):
            return "I'm sorry, but we have exceeded our current quota. Please check back later."
        else:
            return "I'm sorry, but I couldn't process your request at the moment."


@app.route('/')
def index():
    try:
        auth_url = get_spotify_auth_url()
        return render_template('index.html', auth_url=auth_url)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "An error occurred in the index route."

@app.route('/callback')
def callback():
    try:
        auth_code = request.args.get('code')
        token = get_spotify_token(auth_code)
        with open("token.json", "w") as token_file:
            json.dump({"access_token": token}, token_file)
        return render_template('chat.html')
    except Exception as e:
        logger.error(f"Error in callback route: {e}")
        return "An error occurred in the callback route."

def extract_preferences(user_message):
    doc = nlp(user_message)
    genres = []
    artists = []
    for ent in doc.ents:
        if ent.label_ == "MUSIC_GENRE":
            genres.append(ent.text)
        elif ent.label_ == "PERSON":  # Assume artists are recognized as PERSON
            artists.append(ent.text)
    return genres, artists

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message')
        token = get_token()
        sp = Spotify(auth=token)
        
        if 'state' not in session:
            session['state'] = 'initial'
        
        if session['state'] == 'initial':
            genres, artists = extract_preferences(user_message)
            user_preferences["genres"].extend(genres)
            
            if 'recommend' in user_message.lower():
                song_query = user_message.lower().replace('recommend', '').strip()
                if not song_query:
                    return jsonify({"message": "Please specify a song name after 'recommend'."})

                # Search for the song based on user input
                search_results = sp.search(q=song_query, type='track', limit=5)
                if not search_results['tracks']['items']:
                    return jsonify({"message": "Song not found. Please try another song name."})
                
                song = search_results['tracks']['items'][0]
                song_id = song['id']
                song_name = f"{song['artists'][0]['name']} - {song['name']}"
                
                # Get recommendations based on the song
                recommendations = sp.recommendations(seed_tracks=[song_id], limit=10)
                recommended_songs = recommendations['tracks']

                response_message = f"Here are some songs you might like based on {song_name}:<br>" + "<br>".join([f"{track['artists'][0]['name']} - {track['name']}" for track in recommended_songs])
                response_message += "<br>Did you like these recommendations? (yes/no)"
                session['state'] = 'recommendation_feedback'
            
            elif 'similar artist' in user_message.lower():
                artist_query = user_message.lower().replace('similar artist', '').strip()
                if not artist_query:
                    return jsonify({"message": "Please specify an artist name after 'similar artist'."})

                search_results = sp.search(q=artist_query, type='artist', limit=10)
                if not search_results['artists']['items']:
                    return jsonify({"message": "Artist not found. Please try another artist name."})

                artist = search_results['artists']['items'][0]
                artist_id = artist['id']
                artist_name = artist['name']
                
                recommendations = sp.artist_related_artists(artist_id)
                recommended_artists = recommendations['artists']
                
                response_message = f"Here are some artists you might like based on {artist_name}:<br>" + "<br>".join([f"{artist['name']}" for artist in recommended_artists])
                response_message += "<br>Do you like these artists? (yes/no)"
                session['state'] = 'artist_feedback'
            
            elif 'genre' in user_message.lower():
                genre_query = user_message.lower().replace('genre', '').strip()
                if not genre_query:
                    return jsonify({"message": "Please specify a genre after 'genre'."})

                # Get recommendations based on the genre
                search_results = sp.search(q=f"genre:{genre_query}", type='track', limit=50)
                recommended_songs = search_results['tracks']['items']
                random.shuffle(recommended_songs)  # Shuffle the list to get different songs each time
                
                if genre_query not in previous_recommendations["genres"]:
                    previous_recommendations["genres"][genre_query] = []

                unique_artists = {}
                unique_songs = []
                for song in recommended_songs:
                    artist_name = song['artists'][0]['name']
                    if artist_name not in unique_artists and song['id'] not in previous_recommendations["genres"][genre_query]:
                        unique_artists[artist_name] = True
                        unique_songs.append(song)
                        previous_recommendations["genres"][genre_query].append(song['id'])
                    if len(unique_songs) == 5:
                        break

                response_message = f"Here are some songs in the {genre_query} genre:<br>" + "<br>".join([f"{track['artists'][0]['name']} - {track['name']}" for track in unique_songs])
                session['state'] = 'genre_feedback'
            
            else:
                response_message = ask_openai(user_message)

        elif session['state'] in ['recommendation_feedback', 'artist_feedback', 'genre_feedback']:
            if 'yes' in user_message.lower():
                response_message = "Thank you! Do you want to continue using the chatbot? (yes/no)"
                session['state'] = 'continue'
            elif 'no' in user_message.lower():
                response_message = "Thank you for your feedback! Have a great day!"
                session['state'] = 'initial'
            else:
                response_message = "Please answer with 'yes' or 'no'."

        elif session['state'] == 'continue':
            if 'yes' in user_message.lower():
                response_message = "I can help you find song or artist recommendations. Just type 'recommend' followed by a song name, 'similar artist' followed by an artist name, or 'genre' followed by a genre."
                session['state'] = 'initial'
            elif 'no' in user_message.lower():
                response_message = "Thank you for using the chatbot! Have a great day!"
                session['state'] = 'initial'
            else:
                response_message = "Please answer with 'yes' or 'no'."

        return jsonify({"message": response_message})
    except Exception as e:
        logger.error(f"Error in chat route: {e}")
        return jsonify({"message": "An error occurred while processing your request."})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)