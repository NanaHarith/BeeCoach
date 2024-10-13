from flask import Flask, render_template, request, session
import csv
import os
from playsound import playsound

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret_key_here"

# Load words from CSV file
words = []
with open("static/words.csv", "r") as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        words.append(row[0])

@app.route("/")
def index():
    session["score"] = 0
    session["words_correct"] = 0
    session["words_incorrect"] = 0
    return render_template("index.html", words=words)

@app.route("/play_audio", methods=["POST"])
def play_audio():
    word = request.form["word"]
    audio_file = os.path.join("static/audio", f"{word}.mp3")
    playsound(audio_file)
    return "Audio played!"

@app.route("/check_spelling", methods=["POST"])
def check_spelling():
    user_answer = request.form["user_answer"]
    correct_answer = request.form["correct_answer"]
    if user_answer.lower() == correct_answer.lower():
        session["score"] += 1
        session["words_correct"] += 1
        result = "Correct!"
    else:
        session["words_incorrect"] += 1
        result = "Incorrect!"
    return result

@app.route("/next_word", methods=["POST"])
def next_word():
    current_word = request.form["current_word"]
    next_word = words[words.index(current_word) + 1]
    return next_word

if __name__ == "__main__":
    app.run(debug=True)