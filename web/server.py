from flask import Flask, render_template
from map_rotation_parser import get_maps

app = Flask(__name__)

@app.route("/")
def index():
	return render_template('index.html', maps=get_maps())

if __name__ == "__main__":
	app.run(debug=True)