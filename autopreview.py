import os
import previewer
import glob
import sys



def generate_previews(map_directory="../tagpro-maps/", image_directory="./web/static/img/"):

	input_files = glob.glob(map_directory+"*.png")

	for png_file in input_files:
		file_name = os.path.splitext(png_file)[0]
		base_name = os.path.basename(png_file)
		logic_file = file_name+".json"
		
		if not os.path.isfile(logic_file):
			print "Unable to find json for %s" %base_name
			continue

		map_ = previewer.Map(png_file, logic_file)
		preview = map_.preview()
		with open(image_directory+base_name, 'wb') as f:
			f.write(preview.getvalue())
			print "Wrote %s successfully" %base_name

	input_files = set(map(lambda x: os.path.basename(x), input_files))
	output_files = set(map(lambda x: os.path.basename(x), glob.glob(image_directory+"*.png")))

	# files that didn't make it to output
	failed =  input_files-output_files
	# files in both input and output (set intersection)
	total = len( input_files & output_files )
	possible = len(input_files)
	print "%s files written successfully...\n%s failed files:\n%s\n" %(total, len(failed), '\n\t'.join(failed))

if __name__ == "__main__":
	if len(sys.argv) != 3:
		print "> Usage: python autopreview.py map_data_directory image_output_directory"
		exit()
	else:
		map_data_directory = sys.argv[1]
		image_directory = sys.argv[2]
		generate_previews(map_data_directory, image_directory)