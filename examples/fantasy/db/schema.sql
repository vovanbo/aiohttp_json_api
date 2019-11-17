CREATE TABLE authors (
  id integer PRIMARY KEY,
  name text NOT NULL CHECK(name <> ''),
  date_of_birth date NOT NULL,
  date_of_death date,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp
);

-- why on earth anyone would use polymorphic relations is beyond me.
CREATE TABLE photos (
  id integer PRIMARY KEY,
  title text NOT NULL CHECK(title <> ''),
  uri text NOT NULL CHECK(uri <> ''),
  imageable_id integer NOT NULL,
  imageable_type text NOT NULL CHECK (imageable_type <> ''),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp
);

-- i've arbitrarily chosen this to be the hasOne example of polymorphic rels
CREATE TABLE series (
  id integer PRIMARY KEY,
  title text NOT NULL CHECK(title <> ''),
  photo_id int NOT NULL REFERENCES photos(id),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp
);

CREATE TABLE books (
  id integer PRIMARY KEY,
  author_id integer NOT NULL REFERENCES authors(id),
  series_id integer REFERENCES series(id),
  date_published date NOT NULL,
  title text NOT NULL CHECK(title <> ''),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp
);

CREATE TABLE chapters (
  id integer PRIMARY KEY,
  book_id integer NOT NULL REFERENCES books(id),
  title text NOT NULL CHECK(title <> ''),
  ordering integer NOT NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp
);

CREATE TABLE stores (
  id integer PRIMARY KEY,
  name text NOT NULL CHECK(name <> ''),
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp
);

CREATE TABLE books_stores (
  book_id integer NOT NULL REFERENCES books(id),
  store_id integer NOT NULL REFERENCES stores(id)
);
