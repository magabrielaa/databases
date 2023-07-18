DROP TABLE IF EXISTS ri_inspections;
DROP TABLE IF EXISTS ri_restaurants;
DROP TABLE IF EXISTS ri_tweetmatch;
DROP TABLE IF EXISTS ri_linked;

CREATE TABLE ri_restaurants (
    id integer PRIMARY KEY AUTOINCREMENT,
    name varchar(60) NOT NULL,
    facility_type varchar(30),
    address varchar(60),
    city varchar(30),
    state char(2),
    zip char(5),
    latitude real,
    longitude real,
    clean boolean DEFAULT FALSE
);

CREATE TABLE ri_inspections (
    id varchar(16),
    risk varchar(30),
    inspection_date date,
    inspection_type varchar(30),
    results varchar(30),
    violations text,
    restaurant_id int NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (restaurant_id) REFERENCES ri_restaurants
);

CREATE TABLE ri_tweetmatch (
    restaurant_id int,
    tkey varchar(60),
    match varchar(20) CHECK( match IN ('geo','name','both'))  NOT NULL
);

CREATE TABLE ri_linked (
    primary_rest_id int,
    original_rest_id int,
    PRIMARY KEY (primary_rest_id, original_rest_id),
    FOREIGN KEY (primary_rest_id) REFERENCES ri_restaurants,
    FOREIGN KEY (original_rest_id) REFERENCES ri_restaurants
);
