from map_schema import Map, db

rotation = ["the holy see", "big vird", "geokoala", "colors", "star", "center flag", "blast off", "boombox", "simplicity", "bombing run", "swoop", "gamepad", "smirk", "danger zone", "oval", "hyper reactor"]

retired = ["glory hole", "ice rink", "figure 8", "pokeball", "arena", "speedway", "spiders", "hourglass", "yiss 3.2", "shortcut", "clutch",
			"lold", "foozball", "micro", "boosts", "battery", "45", "bounce", "whirlwind", "thinking with portals", "vee"]

MOTW = ["colors", "star"]
MOTM = ["colors"]


def add_status(maps, status):
	for m in maps:
		Map.query.filter(Map.mapname.ilike(m)).first().status = status

add_status(rotation, "inrotation")
add_status(retired, "retired")
add_status(MOTW, "MOTW")
add_status(MOTM, "MOTM")



db.session.commit()
