import os
import glob
from multiprocessing import Pool

from previewer import previewer

OUT_DIR = os.path.abspath("./static/previews/")
MAP_DIR = os.path.abspath("./static/maps/")


def generate_previews(png_path):
    file_name = os.path.splitext(png_path)[0]
    base_name = os.path.basename(png_path)
    json_path = file_name + ".json"
    print file_name
    if not os.path.isfile(json_path):
        print "Unable to find json for %s" % base_name
        return None
    try:
        map_ = previewer.Map(png_path, json_path)
        preview = map_.preview()
        with open(os.path.join(OUT_DIR, base_name, 'wb')) as f:
            f.write(preview.getvalue())
            print "[ ] Wrote {} successfully".format(base_name)
    except:  # TODO: Super broad. Specific exceptions would be good.
        print "[X] Problem with {}".format(png_path)
        pass


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        process_count = 4
    else:
        process_count = int(sys.argv[-1])

    png_files = glob.glob(os.path.join(MAP_DIR, "*.png"))
    p = Pool(process_count)
    p.map(generate_previews, png_files)
