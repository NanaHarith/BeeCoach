import os
import random
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO
import csv
from gtts import gTTS

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app)

words_list = []

def read_words(file):
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        return [row['Words'] for row in reader]

@app.before_request
def before_request():
    if 'score' not in session:
        session['score'] = {'correct': 0, 'incorrect': 0}
        session['correct_words'] = []
        session['incorrect_words'] = []
        session['current_word_index'] = 0
    session.modified = True

@app.route('/')
def index():
    global words_list
    if not words_list:
        words_list = read_words('static/words.csv')

    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0

    return render_template('index.html', total_words=len(words_list), score=session['score'],
                           current_word_number=session['current_word_index'] + 1)

@app.route('/get_audio', methods=['GET'])
def get_audio():
    global words_list
    current_word = words_list[session['current_word_index']]

    # Generate audio data
    tts = gTTS(text=current_word, lang='en')
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)

    # Encode audio data to base64
    audio_data = base64.b64encode(fp.getvalue()).decode('utf-8')

    return jsonify({
        'audio_data': audio_data,
        'word': current_word
    })

@app.route('/start_practice', methods=['POST'])
def start_practice():
    global words_list
    current_word = words_list[session['current_word_index']]
    return jsonify({'success': True, 'word': current_word})

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

    # Increment the word index and reset if necessary
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

@app.route('/next_word')
def next_word():
    global words_list
    session['current_word_index'] += 1
    if session['current_word_index'] >= len(words_list):
        session['current_word_index'] = 0

    current_word = words_list[session['current_word_index']]
    session.modified = True
    return jsonify({
        'word_number': session['current_word_index'] + 1,
        'word': current_word
    })

@app.route('/repeat_word')
def repeat_word():
    global words_list
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
    global words_list
    random.shuffle(words_list)
   # session['current_word_index'] = 0
    current_word = words_list[session['current_word_index']]
    session.modified = True
    return jsonify({
        'success': True,
        'word_number': session['current_word_index'] + 1,
        'word': current_word
    })

if __name__ == '__main__':
    words_list = read_words('static/words.csv')
    print(f"Total words: {len(words_list)}")
    print(f"First word: {words_list[0]}")

    socketio.run(app, allow_unsafe_werkzeug=True, debug=True)
