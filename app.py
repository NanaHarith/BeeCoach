import os
import csv
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_file

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Ensure you set your secret key here

# Correct path to words.csv in the static directory
csv_file_path = os.path.join(app.root_path, 'static', 'words.csv')


def load_words():
    words = []
    with open(csv_file_path, newline='') as csvfile:
        word_reader = csv.reader(csvfile)
        for row in word_reader:
            words.append(row[0])
    return words


def initialize_session():
    words = load_words()  # Load words from CSV file
    session['words'] = words
    session['current_word_index'] = 0
    session['correct_score'] = 0
    session['incorrect_score'] = 0
    print("Session initialized:", session)  # Debugging output


@app.route('/')
def index():
    initialize_session()  # Initialize session variables on first visit
    return render_template('index.html', total_words=len(session['words']), current_word_number=1,
                           score={'correct': 0, 'incorrect': 0})


@app.route('/start_practice', methods=['POST'])
def start_practice():
    initialize_session()  # Ensure the session is initialized for practice
    print("Start practice called")
    return jsonify(success=True)


@app.route('/next_word')
def next_word():
    words = session.get('words', [])
    current_word_index = session.get('current_word_index', 0)

    print(f"Current word index before increment: {current_word_index}")

    if current_word_index < len(words):
        current_word = words[current_word_index]
        session['current_word_index'] += 1  # Move to the next word
        score = {'correct': session.get('correct_score', 0), 'incorrect': session.get('incorrect_score', 0)}
        print(f"Current word: {current_word}, Index: {current_word_index}")
        return render_template('index.html', word=current_word, total_words=len(words),
                               current_word_number=current_word_index + 1, score=score)
    else:
        return redirect(url_for('results'))


@app.route('/submit', methods=['POST'])
def submit():
    user_input = request.form['user_input'].strip().lower()
    words = session.get('words', [])
    current_word_index = session.get('current_word_index', 0) - 1
    current_word = words[current_word_index].strip().lower()

    print(f"User input: {user_input}, Correct word: {current_word}")

    if user_input == current_word:
        session['correct_score'] = session.get('correct_score', 0) + 1
    else:
        session['incorrect_score'] = session.get('incorrect_score', 0) + 1

    return redirect(url_for('next_word'))


@app.route('/results')
def results():
    correct_score = session.get('correct_score', 0)
    incorrect_score = session.get('incorrect_score', 0)
    return render_template('results.html', correct_score=correct_score, incorrect_score=incorrect_score)


@app.route('/reset', methods=['POST'])
def reset():
    initialize_session()  # Reset session variables
    return jsonify(success=True, score={'correct': 0, 'incorrect': 0}, word_number=1)


@app.route('/repeat_word')
def repeat_word():
    return jsonify(success=True)


@app.route('/get_audio')
def get_audio():
    words = session.get('words', [])
    current_word_index = session.get('current_word_index', 0) - 1  # Adjust for index

    print(f"Current word index for audio: {current_word_index}")
    if current_word_index < 0 or current_word_index >= len(words):
        print("Error: Current word index is out of bounds")
        return jsonify(success=False), 404  # Return 404 if the index is out of bounds

    current_word = words[current_word_index]
    audio_file_path = os.path.join(app.static_folder, 'audio', f'{current_word}.mp3')

    print(f"Looking for audio file at: {audio_file_path}")
    if not os.path.exists(audio_file_path):
        print("Error: Audio file does not exist")
        return jsonify(success=False), 404  # Return 404 if the audio file does not exist

    return send_file(audio_file_path, mimetype='audio/mpeg')


if __name__ == "__main__":
    app.run(debug=True)
