from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run()


### src for video :
# src="{{ url_for('static', filename='test-files/test.mp4') }}"
# href for index.html 
#   href="{{ url_for('static', filename= sjfnsjks'AgentPageIndexStyle.css') }}"
