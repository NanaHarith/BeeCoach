from flask import Flask, render_template, jsonify, send_from_directory
import csv
import os

app = Flask(__name__)

# Load words from CSV
def load_words():
    with open('static/words.csv', 'r') as file:
        reader = csv.reader(file)
        return [row[0] for row in reader]

words = load_words()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/words')
def get_words():
    return jsonify(words)

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('static/audio', filename)

@app.route('/results')
def results():
    return render_template('results.html')

if __name__ == '__main__':
    app.run(debug=True)