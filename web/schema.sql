drop table if exists maps;
create table maps (
  id integer primary key autoincrement,
  mapname text not null,
  upload_time real,
  times_tested integer,
  last_tested real
);

drop table if exists search;
create virtual table search using fts4(
	mapname,
	author,
	description
);

