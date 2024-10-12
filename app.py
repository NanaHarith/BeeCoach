import os
import csv
from flask import Flask, render_template, request, session, redirect, url_for
from gtts import gTTS
import random

app = Flask(__name__)
app.secret_key = os.urandom(24) # Make sure you set your secret key here

# Correct path to words.csv in the static directory
csv_file_path = os.path.join(app.root_path, 'static', 'words.csv')


def load_words():
    words = []
    with open(csv_file_path, newline='') as csvfile:
        word_reader = csv.reader(csvfile)
        for row in word_reader:
            words.append(row[0])
    return words


@app.route('/')
def index():
    words = load_words()  # Load words from CSV file
    session['words'] = words
    session['current_word_index'] = 0
    session['correct_score'] = 0
    session['incorrect_score'] = 0
    return render_template('index.html')


@app.route('/next_word')
def next_word():
    words = session.get('words', [])
    current_word_index = session.get('current_word_index', 0)

    if current_word_index < len(words):
        current_word = words[current_word_index]
        session['current_word_index'] = current_word_index + 1
        return render_template('index.html', word=current_word)
    else:
        return redirect(url_for('results'))


@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        user_input = request.form['word'].strip().lower()
        words = session.get('words', [])
        current_word_index = session.get('current_word_index', 0) - 1
        current_word = words[current_word_index].strip().lower()

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


if __name__ == "__main__":
    app.run(allow_unsafe_werkzeug=True, debug=True)
