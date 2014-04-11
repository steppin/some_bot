from map_schema import Map, db

rotation = ["the holy see", "big vird", "geokoala", "colors", "star", "center flag", "blast off", "boombox", "simplicity", "bombing run", "swoop", "gamepad", "smirk", "danger zone", "oval", "hyper reactor"]

for m in rotation:
	Map.query.filter(Map.mapname.ilike(m)).first().status = "inrotation"

retired = ["glory hole", "ice rink", "figure 8", "pokeball", "arena", "speedway", "spiders", "hourglass", "yiss 3.2", "shortcut", "clutch",
			"lold", "foozball", "micro", "boosts", "battery", "45", "bounce", "whirlwind", "thinking with portals", "vee"]

for m in retired:
	Map.query.filter(Map.mapname.ilike(m)).first().status = "retired"

db.session.commit()
