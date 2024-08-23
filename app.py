import os
import time
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO
import csv
from threading import Thread
import queue
from gtts import gTTS

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app)

words_list = []
audio_queue = queue.Queue()

def read_words(file):
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        return [row['Words'] for row in reader]

def play_audio_worker():
    while True:
        text = audio_queue.get()
        if text is None:
            break
        tts = gTTS(text=text, lang='en')
        file_name = 'tempWord.mp3'
        file_path = os.path.join('static', file_name)
        tts.save(file_path)

        # Confirm file creation and allow some time for writing
        for _ in range(5):  # Retry 5 times with delay to ensure file is written
            if os.path.exists(file_path):
                full_path = os.path.abspath(file_path)
                print(full_path)
                print(f"File created successfully: {full_path}")
                break
            time.sleep(.2)  # Adjust delay as necessary
        else:
            print(f"Error: File not found after creation attempt: {file_path}")

        audio_queue.task_done()

@app.before_request
def before_request():
    if 'score' not in session:
        session['score'] = {'correct': 0, 'incorrect': 0}
        session['correct_words'] = []
        session['incorrect_words'] = []
        session['current_word_index'] = 0

@app.route('/')
def index():
    global words_list
    if not words_list:
        words_list = read_words('static/words.csv')

    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0

    return render_template('index.html', total_words=len(words_list), score=session['score'],
                           current_word_number=session['current_word_index'] + 1)

@app.route('/start_practice', methods=['POST'])
def start_practice():
    global words_list
    current_word = words_list[session['current_word_index']]
    audio_queue.put(current_word)
    return jsonify({'success': True})

@app.route('/submit', methods=['POST'])
def submit():
    global words_list
    user_input = request.form['user_input']
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
    audio_queue.put(next_word)

    session.modified = True
    return jsonify({
        'result': result,
        'score': session['score'],
        'next_word_number': session['current_word_index'] + 1
    })

@app.route('/next_word')
def next_word():
    global words_list
    session['current_word_index'] += 1
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0

    current_word = words_list[session['current_word_index']]
    audio_queue.put(current_word)
    session.modified = True
    return jsonify({
        'word_number': session['current_word_index'] + 1
    })

@app.route('/repeat_word')
def repeat_word():
    global words_list
    current_word = words_list[session['current_word_index']]
    audio_queue.put(current_word)
    return jsonify({
        'success': True
    })

@app.route('/results')
def results():
    return render_template('results.html', score=session['score'],
                           correct_words=session['correct_words'],
                           incorrect_words=session['incorrect_words'])

if __name__ == '__main__':
    words_list = read_words('static/words.csv')
    print(f"Total words: {len(words_list)}")
    print(f"First word: {words_list[0]}")

    # Start the audio worker thread
    audio_thread = Thread(target=play_audio_worker)
    audio_thread.start()

    socketio.run(app, allow_unsafe_werkzeug=True, debug=True)
