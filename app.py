import os
import random
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import csv
import threading
import queue
import time
from functools import lru_cache
from gtts import gTTS

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app)

# Use thread-local storage for session-like data
from threading import local
thread_local = local()

# Global variables
words_list = []
audio_cache = {}
audio_queue = queue.Queue()

def read_words(file):
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        words = [row['Words'] for row in reader]
    print(f"Loaded {len(words)} words from {file}")
    return words

@lru_cache(maxsize=1000)
def generate_audio(word):
    tts = gTTS(text=word, lang='en')
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return base64.b64encode(fp.getvalue()).decode('utf-8')

def audio_worker():
    while True:
        word = audio_queue.get()
        if word not in audio_cache:
            try:
                audio_cache[word] = generate_audio(word)
            except Exception as e:
                print(f"Error generating audio for '{word}': {str(e)}")
        audio_queue.task_done()

def initialize_app():
    global words_list
    if not words_list:
        words_list = read_words('static/words.csv')
        for word in words_list:
            audio_queue.put(word)

        for _ in range(4):  # Start 4 worker threads
            threading.Thread(target=audio_worker, daemon=True).start()

@app.before_request
def before_request():
    initialize_app()
    if not hasattr(thread_local, 'session_data'):
        thread_local.session_data = {
            'score': {'correct': 0, 'incorrect': 0},
            'correct_words': [],
            'incorrect_words': [],
            'current_word_index': 0
        }

def get_session_data():
    return thread_local.session_data

def update_session_data(key, value):
    thread_local.session_data[key] = value

@app.route('/')
def index():
    session_data = get_session_data()
    if session_data['current_word_index'] >= len(words_list):
        update_session_data('current_word_index', 0)
    return render_template('index.html', total_words=len(words_list), score=session_data['score'],
                           current_word_number=session_data['current_word_index'] + 1)

@app.route('/get_audio', methods=['GET'])
def get_audio():
    session_data = get_session_data()
    if session_data['current_word_index'] >= len(words_list):
        update_session_data('current_word_index', 0)
    current_word = words_list[session_data['current_word_index']]

    # Wait for audio to be generated (with timeout)
    timeout = time.time() + 10  # 10 second timeout
    while current_word not in audio_cache:
        time.sleep(0.1)
        if time.time() > timeout:
            return jsonify({'error': 'Audio generation timed out'}), 500

    return jsonify({
        'audio_data': audio_cache[current_word],
        'word': current_word
    })

@app.route('/start_practice', methods=['POST'])
def start_practice():
    session_data = get_session_data()
    if session_data['current_word_index'] >= len(words_list):
        update_session_data('current_word_index', 0)
    current_word = words_list[session_data['current_word_index']]
    return jsonify({'success': True, 'word': current_word})

@app.route('/submit', methods=['POST'])
def submit():
    user_input = request.form['user_input']
    session_data = get_session_data()
    if session_data['current_word_index'] >= len(words_list):
        update_session_data('current_word_index', 0)
    current_word = words_list[session_data['current_word_index']]

    if user_input.lower() == current_word.lower():
        result = "Correct!"
        session_data['score']['correct'] += 1
        session_data['correct_words'].append(current_word)
    else:
        result = f"Incorrect. The correct spelling is: {current_word}"
        session_data['score']['incorrect'] += 1
        session_data['incorrect_words'].append(current_word)

    session_data['current_word_index'] += 1
    if session_data['current_word_index'] >= len(words_list):
        update_session_data('current_word_index', 0)

    next_word = words_list[session_data['current_word_index']]

    return jsonify({
        'result': result,
        'score': session_data['score'],
        'next_word_number': session_data['current_word_index'] + 1,
        'word': next_word
    })

@app.route('/next_word', methods=['GET'])
def next_word():
    session_data = get_session_data()
    session_data['current_word_index'] += 1
    if session_data['current_word_index'] >= len(words_list):
        update_session_data('current_word_index', 0)

    current_word = words_list[session_data['current_word_index']]
    return jsonify({
        'word_number': session_data['current_word_index'] + 1,
        'word': current_word
    })

@app.route('/repeat_word', methods=['GET'])
def repeat_word():
    session_data = get_session_data()
    if session_data['current_word_index'] >= len(words_list):
        update_session_data('current_word_index', 0)
    current_word = words_list[session_data['current_word_index']]
    return jsonify({
        'success': True,
        'word': current_word
    })

@app.route('/reset', methods=['POST'])
def reset():
    update_session_data('score', {'correct': 0, 'incorrect': 0})
    update_session_data('correct_words', [])
    update_session_data('incorrect_words', [])
    update_session_data('current_word_index', 0)
    session_data = get_session_data()
    return jsonify({
        'success': True,
        'score': session_data['score'],
        'word_number': session_data['current_word_index'] + 1
    })

@app.route('/results')
def results():
    session_data = get_session_data()
    return render_template('results.html', score=session_data['score'],
                           correct_words=session_data['correct_words'],
                           incorrect_words=session_data['incorrect_words'])

@app.route('/randomize', methods=['POST'])
def randomize():
    global words_list
    random.shuffle(words_list)
    session_data = get_session_data()
    current_word = words_list[session_data['current_word_index']]
    return jsonify({
        'success': True,
        'word_number': session_data['current_word_index'] + 1,
        'word': current_word
    })

if __name__ == '__main__':
    socketio.run(app, debug=True)