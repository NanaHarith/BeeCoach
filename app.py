import os
import random
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO
import csv
from gtts import gTTS
import threading
import queue
import time
from functools import lru_cache

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app)

words_list = []
audio_cache = {}
audio_queue = queue.Queue()
initialization_done = False

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
    global words_list, initialization_done
    if not initialization_done:
        words_list = read_words('static/words.csv')
        for word in words_list:
            audio_queue.put(word)

        for _ in range(4):  # Start 4 worker threads
            threading.Thread(target=audio_worker, daemon=True).start()

        initialization_done = True

@app.before_request
def before_request():
    initialize_app()
    if 'score' not in session:
        session['score'] = {'correct': 0, 'incorrect': 0}
        session['correct_words'] = []
        session['incorrect_words'] = []
        session['current_word_index'] = 0
    session.modified = True

@app.route('/')
def index():
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0
    return render_template('index.html', total_words=len(words_list), score=session['score'],
                           current_word_number=session['current_word_index'] + 1)

@app.route('/get_audio', methods=['GET'])
def get_audio():
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0
    current_word = words_list[session['current_word_index']]

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
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0
    current_word = words_list[session['current_word_index']]
    return jsonify({'success': True, 'word': current_word})

@app.route('/submit', methods=['POST'])
def submit():
    user_input = request.form['user_input']
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0
    current_word = words_list[session['current_word_index']]

    if user_input.lower() == current_word.lower():
        result = "Correct!"
        session['score']['correct'] += 1
        session['correct_words'].append(current_word)
    else:
        result = f"Incorrect. The correct spelling is: {current_word}"
        session['score']['incorrect'] += 1
        session['incorrect_words'].append(current_word)

    session['current_word_index'] += 1
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0

    next_word = words_list[session['current_word_index']]
    session.modified = True

    return jsonify({
        'result': result,
        'score': session['score'],
        'next_word_number': session['current_word_index'] + 1,
        'word': next_word
    })

@app.route('/next_word', methods=['GET'])
def next_word():
    session['current_word_index'] += 1
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0

    current_word = words_list[session['current_word_index']]
    session.modified = True
    return jsonify({
        'word_number': session['current_word_index'] + 1,
        'word': current_word
    })

@app.route('/repeat_word', methods=['GET'])
def repeat_word():
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0
    current_word = words_list[session['current_word_index']]
    return jsonify({
        'success': True,
        'word': current_word
    })

@app.route('/reset', methods=['POST'])
def reset():
    session['score'] = {'correct': 0, 'incorrect': 0}
    session['correct_words'] = []
    session['incorrect_words'] = []
    session['current_word_index'] = 0
    session.modified = True
    return jsonify({
        'success': True,
        'score': session['score'],
        'word_number': session['current_word_index'] + 1
    })

@app.route('/results')
def results():
    return render_template('results.html', score=session['score'],
                           correct_words=session['correct_words'],
                           incorrect_words=session['incorrect_words'])

@app.route('/randomize', methods=['POST'])
def randomize():
    random.shuffle(words_list)
    current_word = words_list[session['current_word_index']]
    session.modified = True
    return jsonify({
        'success': True,
        'word_number': session['current_word_index'] + 1,
        'word': current_word
    })

if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True)