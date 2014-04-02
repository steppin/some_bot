drop table if exists maps;
create table maps (
  id integer primary key autoincrement,
  mapname text not null,
  author text,
  upload_time real,
  times_tested integer,
  last_tested real
);
