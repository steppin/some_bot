drop table if exists maps;
create table maps (
  id integer primary key autoincrement,
  mapname text unique not null
);
