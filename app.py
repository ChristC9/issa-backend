from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from google.cloud import firestore
import random
import string
import uuid
from firebase_admin import credentials, firestore, initialize_app
import os

load_dotenv()
app = Flask(__name__)

# Update CORS configuration to explicitly allow all routes and methods
CORS(app, 
     resources={r"/api/*": {
         "origins": ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"], 
         "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization", "Accept"]
     }},
     supports_credentials=False)

cred = credentials.Certificate(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
default_app = initialize_app(cred)
db = firestore.client()
games_ref = db.collection('wordle_games')

with open('words.txt', 'r') as f:
    WORDS = [word.strip().upper() for word in f.readlines() if len(word.strip()) == 5]

# If words.txt doesn't exist, use a small set of words for testing
if not WORDS:
    WORDS = ["APPLE", "HOUSE", "PIANO", "GHOST", "TRAIN", "SMILE", "BEACH", "CLOCK"]

def get_random_word():
    return random.choice(WORDS)

def is_valid_word(word):
    return word.upper() in WORDS

def calculate_letter_status(guess, solution):
    """Calculate status for each letter in the guess"""
    result = ["absent"] * 5
    solution_chars = list(solution)
    
    # First pass: mark correct positions
    for i in range(5):
        if guess[i] == solution[i]:
            result[i] = "correct"
            solution_chars[i] = None  # Mark as used
    
    # Second pass: mark present letters
    for i in range(5):
        if result[i] == "absent" and guess[i] in solution_chars:
            result[i] = "present"
            solution_chars[solution_chars.index(guess[i])] = None  # Mark as used
    
    return result

def calculate_key_statuses(guesses, solution):
    """Calculate status for each key on the keyboard"""
    key_statuses = {}
    
    # Initialize all letters as unused
    for letter in string.ascii_uppercase:
        key_statuses[letter] = "unused"
    
    # Update based on guesses
    for guess in guesses:
        word = guess["word"]
        for i, letter in enumerate(word):
            current_status = key_statuses[letter]
            letter_result = calculate_letter_status(word, solution)[i]
            
            # Only upgrade status (unused -> absent -> present -> correct)
            status_priority = {"unused": 0, "absent": 1, "present": 2, "correct": 3}
            if status_priority.get(letter_result, 0) > status_priority.get(current_status, 0):
                key_statuses[letter] = letter_result
    
    return key_statuses

@app.route('/api/hello', methods=['GET'])
def sayHello():
    
    data = {
        'message' : 'Hey, I am a Flask API',
        'status' : 200
    }

    return jsonify(data)

@app.route('/api/wordle/game', methods=['POST'])
def create_game():
    solution = get_random_word()
    game_id = str(uuid.uuid4())
    
    game_data = {
        'gameId': game_id,
        'solution': solution,
        'guesses': [],
        'gameOver': False,
        'won': False,
        'createdAt': firestore.SERVER_TIMESTAMP
    }
    
    games_ref.document(game_id).set(game_data)
    
    return jsonify({
        'gameId': game_id,
        'message': 'New game created successfully',
        'solution': solution if app.debug else None  # Only return solution in debug mode
    })

@app.route('/api/wordle/game/<game_id>/guess', methods=['POST'])
def submit_guess(game_id):
    data = request.json
    guess = data.get('guess', '').upper()
    
    # Validate guess
    if len(guess) != 5:
        return jsonify({'error': 'Guess must be 5 letters'}), 400
    
    if not guess.isalpha():
        return jsonify({'error': 'Guess must contain only letters'}), 400
    
    if not is_valid_word(guess):
        return jsonify({'error': 'Not a valid word'}), 400
    
    # Get game data
    game_doc = games_ref.document(game_id).get()
    if not game_doc.exists:
        return jsonify({'error': 'Game not found'}), 404
    
    game_data = game_doc.to_dict()
    
    # Check if game is already over
    if game_data.get('gameOver', False):
        return jsonify({'error': 'Game is already over'}), 400
    
    solution = game_data['solution']
    guesses = game_data.get('guesses', [])
    
    # Check if max attempts reached
    if len(guesses) >= 6:
        game_data['gameOver'] = True
        games_ref.document(game_id).update({'gameOver': True})
        return jsonify({'error': 'Maximum attempts reached'}), 400
    
    # Process the guess
    letter_statuses = calculate_letter_status(guess, solution)
    guess_data = {
        'word': guess,
        'statuses': letter_statuses
    }
    
    guesses.append(guess_data)
    game_data['guesses'] = guesses
    
    # Check if won
    won = (guess == solution)
    
    # Check if this was the last attempt (6th guess)
    is_last_attempt = len(guesses) >= 6
    
    # Game is over if player won or used all attempts
    game_over = won or is_last_attempt
    
    game_data['won'] = won
    game_data['gameOver'] = game_over
    
    # Update game in database - ensure we're updating all fields
    games_ref.document(game_id).update({
        'guesses': guesses,
        'won': won,
        'gameOver': game_over
    })
    
    # Calculate key statuses
    key_statuses = calculate_key_statuses(guesses, solution)
    
    response = {
        'guesses': guesses,
        'keyStatuses': key_statuses,
        'gameOver': game_over,
        'won': won,
        'message': 'Correct! You won!' if won else 'Guess submitted'
    }
    
    if game_over and not won:
        response['message'] = f'Game over. The word was {solution}.'
        response['solution'] = solution
    
    return jsonify(response)

@app.route('/api/wordle/game/<game_id>', methods=['GET'])
def get_game_state(game_id):
    game_doc = games_ref.document(game_id).get()
    if not game_doc.exists:
        return jsonify({'error': 'Game not found'}), 404
    
    game_data = game_doc.to_dict()
    guesses = game_data.get('guesses', [])
    
    return jsonify({
        'guesses': guesses,
        'remainingAttempts': 6 - len(guesses),
        'gameOver': game_data.get('gameOver', False),
        'won': game_data.get('won', False),
        'message': 'Game in progress'
    })

@app.route('/api/wordle/game/<game_id>/key-statuses', methods=['GET'])
def get_key_statuses(game_id):
    game_doc = games_ref.document(game_id).get()
    if not game_doc.exists:
        return jsonify({'error': 'Game not found'}), 404
    
    game_data = game_doc.to_dict()
    guesses = game_data.get('guesses', [])
    solution = game_data.get('solution', '')
    
    key_statuses = calculate_key_statuses(guesses, solution)
    
    return jsonify(key_statuses)

if __name__ == '__main__':
    app.run(debug=True)