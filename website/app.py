from flask import Flask, render_template, url_for


app = Flask(__name__)

@app.context_processor
def inject_hermes_assets():
    return {
        'HermesLogo': url_for('static', filename='test-files/HermesLogoSoloTransparent.png'),
        'HermesName': url_for('static', filename='test-files/HermesLettersTransparent.png')
    }

@app.route("/")
def index():
    mainvideo = url_for('static', filename='test-files/test.mp4')
    return render_template('index.html', video = mainvideo)

@app.route("/previousnews")
def previousnews():
    linknews1 = url_for('static', filename='test-files/one.jpeg')
    linknews2 = url_for('static', filename='test-files/two.jpg')
    linknews3 = url_for('static', filename='test-files/three.webp')
    linknews4 = url_for('static', filename='test-files/four.jpg')
    linknews5 = url_for('static', filename='test-files/five.webp')
    linknews6 = url_for('static', filename='test-files/six.jpg')
    linknews7 = url_for('static', filename='test-files/seven.webp')
    linknews8 = url_for('static', filename='test-files/eight.webp')
    linknews9 = url_for('static', filename='test-files/nine.webp')

    return render_template('previousnews.html',news1 = linknews1,news2 = linknews2,news3 = linknews3,news4 = linknews4,news5 = linknews5,news6 = linknews6,news7 = linknews7,news8 = linknews8,news9 = linknews9)

@app.route("/sources")
def sources():
    return render_template('sources.html')

@app.route("/team")
def team():
    return render_template('team.html')

if __name__ == "__main__":
    # debug=True helps during development (auto-reload and better error pages)
    app.run(debug=True)


### src for video :
# src="{{ url_for('static', filename='test-files/test.mp4') }}"
# href for index.html 
#   href="{{ url_for('static', filename= sjfnsjks'AgentPageIndexStyle.css') }}"
