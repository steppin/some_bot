from flask import Flask, render_template, request, jsonify
#from map_rotation_parser import get_maps
import requests
import os
from glob import glob


app = Flask(__name__)

map_data_directory = "./maps/"
map_preview_directory = "./static/img/"

def get_maps(map_previews=map_preview_directory):
	maps = []
	for image_path in glob(map_previews+"*.png"):
		base_name = os.path.basename(image_path)
		map_name = os.path.splitext(base_name)[0]
		maps.append({"name":map_name, "url":"/static/img/"+base_name, "author":"author", "description":"description", "tags":['cool','nice']})
	return maps

def get_logic_layout_files(map_name):
	logic = map_data_directory+map_name+".json"
	layout = map_data_directory+map_name+".png"
	if os.path.isfile(logic) and os.path.isfile(layout):
		return {'logic':open(logic), 'layout':open(layout)}

@app.route("/")
def index():
	maps = get_maps()
	print maps
	return render_template('index.html', maps=maps)

@app.route('/maptest', methods=['get', 'post'])
def get_testmap_url():
	testmap = request.args.get('mapname', None)
	print 'Testmap: ', testmap
	clean_map_name = testmap.lower().replace('motw', '').strip()
	test_server = 'http://tagpro-maptest.koalabeast.com/testmap'
	files = get_logic_layout_files(testmap)
	r = requests.post(test_server, files=files)
	print r.url
	return jsonify(success=True, testurl=r.url)

if __name__ == "__main__":
	app.run(debug=True)