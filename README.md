# Wordle Clone Backend

This is a Flask backend for a Wordle clone game. It provides the necessary API endpoints to create and play Wordle games.

## Setup Instructions

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up Firebase:
   - Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
   - Generate a new private key in Project Settings > Service Accounts
   - Save the JSON file as `your_filename.json` in the root directory of this project

4. Run the application:
   ```
   create a .env file and add the following:
   GOOGLE_APPLICATION_CREDENTIALS = "current_directory/your_filename.json"
   python app.py
   ```

## API Endpoints

### Create a new game
```
POST /api/wordle/game
```
Returns:
```json
{
  "gameId": "unique-game-id",
  "message": "New game created successfully",
  "solution": "WORD" // Only in debug mode
}
```

### Submit a guess
```
POST /api/wordle/game/:gameId/guess
```
Body:
```json
{
  "guess": "WORD"
}
```
Returns:
```json
{
  "guesses": [
    {
      "word": "WORD",
      "statuses": ["correct", "absent", "present", "absent", "correct"]
    }
  ],
  "keyStatuses": {
    "A": "unused",
    "B": "absent",
    // ... other keys
  },
  "gameOver": false,
  "won": false,
  "message": "Guess submitted"
}
```

### Get game state
```
GET /api/wordle/game/:gameId
```
Returns:
```json
{
  "guesses": [
    {
      "word": "WORD",
      "statuses": ["correct", "absent", "present", "absent", "correct"]
    }
  ],
  "remainingAttempts": 5,
  "gameOver": false,
  "won": false,
  "message": "Game in progress"
}
```

### Get keyboard key statuses
```
GET /api/wordle/game/:gameId/key-statuses
```
Returns:
```json
{
  "A": "unused",
  "B": "absent",
  "C": "present",
  "D": "correct",
  // ... other keys
}
```

## Game Rules

- Players have 6 attempts to guess a 5-letter word
- After each guess, the game provides feedback on each letter:
  - "correct": The letter is in the word and in the correct position
  - "present": The letter is in the word but in the wrong position
  - "absent": The letter is not in the word
- The game ends when the player guesses the word correctly or uses all 6 attempts 
