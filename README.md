  Spotify Music Recommender Chatbot

This application is a web-based music recommender system built using Flask. It integrates with the Spotify API to provide personalized music recommendations based on user input and leverages the OpenAI API to enhance user interactions with a natural language chatbot interface. The application offers a seamless way to explore new music and artists while interacting with an intelligent assistant capable of understanding and responding to a variety of queries.

About the Application
Purpose
The Spotify Music Recommender Chatbot aims to enhance music discovery by offering personalized recommendations and insights. It serves as a virtual assistant that helps users navigate the vast world of music by providing tailored suggestions based on user preferences, specific songs, artists, or genres.

Key Features
Music Recommendations: Users can get song recommendations by simply entering the name of a track. The system analyzes the selected track and suggests similar songs that match the user's taste.

Artist Suggestions: By entering the name of an artist, users can discover other artists with a similar musical style. This feature helps users explore new music by introducing them to artists they might not have encountered before.

Genre-Based Exploration: Users can request songs from a particular genre, allowing them to explore music styles and discover tracks that fit their current mood or interest.

Intelligent Chatbot Interactions: The application includes a chatbot powered by OpenAI's language models, enabling users to ask questions and receive coherent, context-aware responses. Whether it's music-related or general queries, the chatbot is equipped to provide helpful answers.

Secure Token Handling: The application employs encryption techniques to securely manage Spotify tokens, ensuring that sensitive information remains protected throughout the user session.

Use Cases
Discover New Music: Ideal for music enthusiasts looking to broaden their musical horizons by discovering new songs and artists.
Enhanced User Experience: Offers a conversational interface that allows users to interact naturally, making music discovery intuitive and enjoyable.
Personalized Recommendations: Provides users with suggestions that align with their musical preferences, enhancing their listening experience.
Requirements
Python 3.6+
A Spotify developer account with client credentials
An OpenAI API key

The following Python packages:

Flask
Flask-Session
Flask-Bcrypt
Spotipy
OpenAI
Python-Dotenv
Cryptography
Setup:

Step 1: Clone the Repository
git clone https://github.com/angelinadegay/song-bot.git
cd spotify-recommender-chatbot

Step 2: Install Dependencies
bash
pip install -r requirements.txt

Step 3: Set Up Environment Variables
Create a .env file in the project directory with the following content:

bash

CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
REDIRECT_URI=http://localhost:5000/callback
OPENAI_API_KEY=your_openai_api_key
ENCRYPTION_KEY=your_generated_encryption_key
You can generate an encryption key with the following code snippet:

python
from cryptography.fernet import Fernet

encryption_key = Fernet.generate_key()
print(encryption_key.decode())

Step 4: Run the Application
bash
python app.py
Open your browser and go to http://localhost:5000 to access the application.

Usage
Home Page: Authenticate with Spotify to access music recommendations.
Chat Page: Interact with the chatbot by typing messages in the chat box.
Use "recommend [song name]" to get song recommendations.
Use "similar artist [artist name]" to get artist suggestions.
Use "genre [genre name]" to get genre-based recommendations.
You can ask general questions, and the chatbot will respond using OpenAI.

Security
Spotify tokens are encrypted before storage and decrypted when needed.
Ensure that your .env file is not shared or committed to version control.
License

This project is licensed under the MIT License - see the LICENSE file for details.

Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements.

Contact
For any questions or feedback, please contact your angelinadeg000@gmail.com.
