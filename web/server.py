from flask import Flask, render_template, request, jsonify
#from map_rotation_parser import get_maps
import requests
import os
from glob import glob


app = Flask(__name__)

map_data_directory = "./maps/"
map_preview_directory = "./static/img/"

ALLOWED_EXTENSIONS = set(['png', 'json'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def get_maps(map_previews=map_preview_directory):
	maps = []
	for image_path in glob(map_previews+"*.png"):
		base_name = os.path.basename(image_path)
		map_name = os.path.splitext(base_name)[0]
		maps.append({"name":map_name, "thumbnail":"/static/img/thumbs/"+base_name, "url":"/static/img/"+base_name, "author":"author", "description":"description", "tags":['cool','nice']})
	return maps

def get_logic_layout_files(map_name):
	logic = map_data_directory+map_name+".json"
	layout = map_data_directory+map_name+".png"
	if os.path.isfile(logic) and os.path.isfile(layout):
		return {'logic':open(logic), 'layout':open(layout)}

@app.route("/")
def index():
	maps = get_maps()
	return render_template('index.html', maps=maps)

def get_test_link(file_data):
	test_server = 'http://tagpro-maptest.koalabeast.com/testmap'
	r = requests.post(test_server, files=file_data)
	return r.url

@app.route('/mapupload', methods=["POST"])
def mapupload():
	print "NEW POST REQUEST"
	if request.method == 'POST':
		files = request.files.getlist('file[]')
		logic, layout = None, None
		for f in files:
			if ".png" in f.filename[-4:]:
				layout = f
			elif ".json" in f.filename[-5:]:
				logic = f
		if logic and layout:
			file_data = {'logic':logic.read(), 'layout':layout.read()}
			testurl = get_test_link(file_data)
			return jsonify(success=True, testurl=testurl)
		else:
			return jsonify(success=False)
			
@app.route('/maptest', methods=['GET', 'POST'])
def maptest():
	testmap = request.args.get('mapname', None)
	print 'Testmap: ', testmap
	clean_map_name = testmap.lower().replace('motw', '').strip()
	file_data = get_logic_layout_files(testmap)
	testurl = get_test_link(file_data)
	return jsonify(success=True, testurl=testurl)

if __name__ == "__main__":
	app.run(debug=True)