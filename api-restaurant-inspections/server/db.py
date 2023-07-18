from os import path
import logging # Logging Library
from errors import KeyNotFound, BadRequest, InspError
from datetime import datetime
import textdistance 
from similarity.jarowinkler import JaroWinkler


# Utility factor to allow results to be used like a dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# helper function that converts query result to json list, after cursor has executed a query
# this will not work for all endpoints directly, just the ones where you can translate
# a single query to the required json.
def to_json_list(cursor):
    results = cursor.fetchall()
    headers = [d[0] for d in cursor.description]
    return [dict(zip(headers, row)) for row in results]


"""
Wraps a single connection to the database with higher-level functionality.
"""


class DB:
    def __init__(self, connection):
        self.conn = connection

    def execute_script(self, script_file):
        with open(script_file, "r") as script:
            c = self.conn.cursor()
            # Only using executescript for running a series of SQL commands.
            c.executescript(script.read())
            self.conn.commit()

    def create_script(self):
        """
        Calls the schema/create.sql file
        """
        script_file = path.join("schema", "create.sql")
        if not path.exists(script_file):
            raise InspError("Create Script not found")
        self.execute_script(script_file)

    def seed_data(self):
        """
        Calls the schema/seed.sql file
        """
        script_file = path.join("schema", "seed.sql")
        if not path.exists(script_file):
            raise InspError("Seed Script not found")
        self.execute_script(script_file)

    def find_restaurant(self, restaurant_id):
        """
        Searches for the restaurant with the given ID. Returns None if the
        restaurant cannot be found in the database.
        """
        if not restaurant_id:
            raise InspError("No Restaurant Id", 404)
        c = self.conn.cursor()
        query = """SELECT * FROM ri_restaurants WHERE id = :restaurant_id"""
        c.execute(query, {"restaurant_id": restaurant_id})
        res = to_json_list(c)
        self.conn.commit()
        if len(res) == 0:
            raise KeyError(f"Restaurant ID {restaurant_id} was not found.")
        return res

    def find_inspection(self, inspection_id):
        """
        Searches for the inspection with the given ID. Returns None if the
        inspection cannot be found in the database.
        """
        if not inspection_id:
            raise InspError("No inspection_id", 404)
        c = self.conn.cursor()
        query = """SELECT * FROM ri_inspections WHERE id = :inspection_id"""
        c.execute(query, {"inspection_id": inspection_id})
        res = to_json_list(c)
        self.conn.commit()
        if len(res) == 0:
            raise KeyError(f"Inspection ID {inspection_id} was not found.")
        return res

    def find_inspections(self, restaurant_id):
        """
        Searches for all inspections associated with the given restaurant.
        Returns an empty list if no matching inspections are found.
        """
        if not restaurant_id:
            raise InspError("No Restaurant Id", 404)
        c = self.conn.cursor()
        query = """SELECT id, risk, inspection_date, inspection_type, results, 
                violations FROM ri_inspections WHERE restaurant_id = ? ORDER BY 
                id ASC;"""
        c.execute(query, [restaurant_id])
        res = to_json_list(c)
        self.conn.commit()
        if len(res) == 0:
            raise KeyError(f"Restaurant ID {restaurant_id} does not currently \
                            have any inspections.")
        return res

    def find_rest_by_inspection(self, inspection_id):
        """
        Finds restaurant associated with a given inspection.
        """
        if not inspection_id:
            raise InspError("No Inspection ID", 404)
        c = self.conn.cursor()
        query = """SELECT res.id, res.name, res.facility_type, res.address, 
                res.city, res.state, res.zip, res.zip, res.clean, res.latitude, 
                res.longitude FROM ri_restaurants AS res JOIN ri_inspections AS 
                insp ON res.id = insp.restaurant_id WHERE insp.id = 
                :inspection_id"""
        c.execute(query, {"inspection_id": inspection_id})
        res = to_json_list(c)
        self.conn.commit()
        if len(res) == 0:
            raise KeyError(f"Restaurant not found.")
        return res
    
    def add_inspection_for_restaurant(self, inspection, restaurant):
        """
        Finds or creates the restaurant then inserts the inspection and
        associates it with the restaurant.
        """
        c = self.conn.cursor()
        query = """SELECT id FROM ri_restaurants WHERE name = ? AND 
                address = ?;"""
        c.execute(query, [restaurant["name"], restaurant["address"]])
        results = c.fetchall()

        #(1)Case where restaurant is not in the database
        if len(results) == 0:
            insert_rest = """INSERT INTO ri_restaurants (name, facility_type, 
                          address, city, state, zip, latitude, longitude)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
            c.execute(insert_rest, [restaurant["name"],
                      restaurant["facility_type"], 
                      restaurant["address"],
                      restaurant["city"], 
                      restaurant["state"],
                      restaurant["zip"], 
                      restaurant["latitude"],
                      restaurant["longitude"]])
        
            #(1.1) Now that restaurant is in the database, get restaurant id
            find_id = """SELECT id FROM ri_restaurants WHERE name = ? AND 
                      address = ?;"""
            c.execute(find_id, (restaurant["name"], restaurant["address"]))
            results2 = to_json_list(c)[0]
            new_rest_id = results2["id"]

            # (1.2) Add inspection to the newly created restaurant
            date_adj = inspection["date"] + " 00:00:00"
            inspection["date"] = datetime.strptime(date_adj, 
                                                   "%m/%d/%Y %H:%M:%S")
            insert_insp = """INSERT INTO ri_inspections (id, risk, 
                          inspection_date, inspection_type, results, 
                          violations, restaurant_id) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)"""
            c.execute(insert_insp, [inspection["inspection_id"], 
                                    inspection["risk"],  
                                    inspection["date"], 
                                    inspection["inspection_type"],
                                    inspection["results"],
                                    inspection["violations"], 
                                    new_rest_id])
            return new_rest_id, 201

        # (2) Case where the restaurant is already in the database
        else:
            #(2.1) Find if inspection is in the database
            rest_id = results[0][0]
            find_insp = """SELECT COUNT(1) FROM ri_inspections WHERE id = ?;"""
            c.execute(find_insp, [inspection["inspection_id"]])
            count_results = to_json_list(c)[0]
            found = count_results["COUNT(1)"]
 
            #(2.2) Add inspection to existing restaurant
            if found == 0:
                date_adj = inspection["date"] + " 00:00:00"
                inspection["date"] = datetime.strptime(date_adj,
                                                       "%m/%d/%Y %H:%M:%S")
                insert_insp = """INSERT INTO ri_inspections (id, risk, 
                              inspection_date, inspection_type, results, 
                              violations, restaurant_id) 
                              VALUES (?, ?, ?, ?, ?, ?, ?)"""
                c.execute(insert_insp, [inspection["inspection_id"], 
                                    inspection["risk"],  
                                    inspection["date"], 
                                    inspection["inspection_type"],
                                    inspection["results"],
                                    inspection["violations"], 
                                    rest_id])
                return rest_id, 200

            # (2.3) Case where both restaurant and inspection are 
            # already in the database
            else:
                return rest_id, 200


    def total_inspections(self):
        '''
        Counts total number of inspections in the ri_inspections table.
        '''
        c = self.conn.cursor()
        query = """SELECT COUNT (*) FROM ri_inspections;"""
        c.execute(query)
        res = to_json_list(c)
        return res
    

    def tweet_match(self, ngs, lat, long, tkey):
        '''
        Finds if tweet matches restaurant by name or location and if so, 
        stores tweet key and restaurant id.
        '''
        c = self.conn.cursor()

        # (1) Find tweet matches by restaurant name
        qmarks = ['lower(?)'] * len(ngs)
        name_query = "SELECT id FROM ri_restaurants WHERE LOWER(name)\
                IN (%s);"%(",").join(qmarks)
        c.execute(name_query, ngs)
        # (1.1) Extract restaurant id's matched by name
        name_matches = to_json_list(c)
        name_ids = []
        for result in name_matches:
            name_ids.extend(list(result.values()))
    
        # (2) Find tweet matches by geographic location
        geo_query = """SELECT id FROM ri_restaurants WHERE latitude <= ? + 
                    0.00225001 AND latitude >= ? - 0.00225001 AND longitude
                    <= ? + 0.00302190 AND longitude >= ? -  0.00302190;"""
        c.execute(geo_query,[lat, lat, long, long])
        # (2.2) Extract restaurant id's matched by geographic location
        geo_matches = to_json_list(c)
        geo_ids = []
        for result in geo_matches:
            geo_ids.extend(list(result.values()))
        
        # (3) List of all matched restaurant id's
        all_ids = name_ids + geo_ids

        # (4) Insert tweet matches into the database 
        for id in all_ids:
            if id in name_ids and id not in geo_ids:
                insert_tweet = """INSERT INTO ri_tweetmatch (restaurant_id, 
                               tkey, match) VALUES (?, ?, ?)"""
                c.execute(insert_tweet, [id, tkey, 'name'])
            elif id not in name_ids and id in geo_ids:
                insert_tweet = """INSERT INTO ri_tweetmatch (restaurant_id, 
                               tkey, match) VALUES (?, ?, ?)"""
                c.execute(insert_tweet, [id, tkey, 'geo'])
            elif id in name_ids and id in geo_ids:
                insert_tweet = """INSERT INTO ri_tweetmatch (restaurant_id,
                                tkey, match) VALUES (?, ?, ?)"""
                c.execute(insert_tweet, [id, tkey, 'both'])

        # (5) Sort matched rest id's in ascending order
        sorted_ids = sorted(all_ids) 
        return sorted_ids

    def find_tweets(self, restaurant_id):
        '''
        Given a restaurant id, finds list of matched tweets and how 
        they were matched.
        '''
        if not restaurant_id:
            raise InspError("No Restaurant ID provided", 404)
        c = self.conn.cursor()
        query = """SELECT DISTINCT tkey, match FROM ri_tweetmatch WHERE 
                restaurant_id = ? ORDER BY tkey"""
        c.execute(query, [restaurant_id])
        res = to_json_list(c)
        self.conn.commit()
        
        if len(res) == 0:
            raise KeyError(f"No associated tweets found")
        return res

    
    def block_records(self, is_blocking_on):
        '''
        If blocking set to True, creates blocks of the data based on ZIP code and 
        cleans the records. If set to False, compares dirty records to all records 
        in the ri_restaurants table to find matches and cleans records.
        '''
        c = self.conn.cursor()

        if is_blocking_on is False:
            # 1) Get all unclean records from database
            query1 = """SELECT * FROM ri_restaurants WHERE clean = 0;"""
            c.execute(query1)
            dirty_restaurants = to_json_list(c)
            # 2) Get all records from database
            query2 = """SELECT * FROM ri_restaurants;"""
            c.execute(query2)
            all_restaurants = to_json_list(c)
            # 3) Clean all records
            self.clean_up(dirty_restaurants, all_restaurants)

        else:
            zip_query = """SELECT DISTINCT zip FROM ri_restaurants;"""
            c.execute(zip_query) 
            zip_list = to_json_list(c)

            for zip_dict in zip_list:
                zip_code = zip_dict.get("zip")
                temp_query = f"""CREATE TEMP TABLE zip_block AS SELECT id, name,  
                            address, city, state, zip, clean, SUBSTR(name, 1, 1) AS idx
                            FROM ri_restaurants WHERE zip = {zip_code};"""           
                c.execute(temp_query)
                idx_query = """CREATE INDEX rest_idx ON zip_block (idx);"""
                c.execute(idx_query)
                # 1) Get all unclean records from temp table
                get_clean = """SELECT * FROM zip_block WHERE clean = 0;"""
                c.execute(get_clean)
                dirty_restaurants = to_json_list(c)
                # 2) Get all records from temp table
                get_all = """SELECT * FROM zip_block;"""
                c.execute(get_all)
                all_restaurants = to_json_list(c)
                # 3) Clean records by block
                self.clean_up(dirty_restaurants, all_restaurants)
                # 4) Drop temp table
                drop_query = """DROP TABLE IF EXISTS zip_block;"""
                c.execute(drop_query)


    def clean_up(self, dirty, all_res, threshold=0.8):
        '''
        Cleans up all dirty records and updates the ri_restaurants, ri_inspections
        and ri_linked tables, accordingly.
        '''
        c = self.conn.cursor()

        # Iterate through every dirty record and compare to every restaurant record
        matches = {} # Initialize dictionary of records matched to a dirty restaurant id
        for dirty_res in dirty:
            matches[dirty_res["id"]] = set()
            for res in all_res:
                # Apply similarity method to each pair of restaurants
                score = self.find_similarity(dirty_res, res) 
                if score:
                    if score >= threshold:
                        matches[dirty_res["id"]].add(res["id"])
                # Update set of dirty records to clean
                update_clean = "UPDATE ri_restaurants SET clean = 1 WHERE id = ?;"
        # Temporary matched pairs (including separated matches and duplicates)
        temp_matches = set() 
        for k, v in matches.items():
            for key, val in matches.items():
                if key in v:
                    new_v = matches.get(k)
                    for value in val:
                        new_v.add(value)
                    matches[k] = new_v
                    temp_matches.add(key)
        # List of matched pairs without duplicates
        final_match_list = []
        for match in temp_matches:
            removed_item = matches.pop(match)
            if removed_item not in final_match_list:
                final_match_list.append(removed_item)
        # Iterate through list of matches to create lists of matched attributes
        for match_sets in final_match_list: 
            temp_list_of_names = []
            temp_list_of_addresses = []
            for ids in match_sets: 
                for res in all_res:
                    if res["id"] == ids:
                        temp_list_of_names.append(res["name"])
                        temp_list_of_addresses.append(res["address"])
            # Find longest strings for name and address between first two records
            # (to compose new primary restaurant record)
            longest_name = max(temp_list_of_names[0], temp_list_of_names[1])
            longest_address = max(temp_list_of_addresses)       
            # Insert primary restaurant record into ri-restaurants table
            insert_primary_rest = """INSERT INTO ri_restaurants (name, address)
                                VALUES (?, ?)"""
            c.execute(insert_primary_rest, [longest_name,
                                            longest_address])
            self.conn.commit()
            primary_rest_id = c.lastrowid # Get primary restaurant record id
            # Initialize dictionary of primary key mapped to list of linked restaurants
            authoritative_key_dict = {} 
            authoritative_key_dict[primary_rest_id] = match_sets

            # Update set of newly created primary record to clean
            update_clean = "UPDATE ri_restaurants SET clean = 1 WHERE id = ?;"
            c.execute(update_clean, [primary_rest_id])  

            for ids in match_sets: 
                insert_match = """INSERT INTO ri_linked (primary_rest_id, 
                            original_rest_id) VALUES (?, ?)"""
                c.execute(insert_match, [primary_rest_id, ids])
                self.conn.commit()
                # Update ri_inspections table for all matched records                
                update_insp = """UPDATE ri_inspections SET restaurant_id = ? 
                            WHERE restaurant_id = ?;"""
                c.execute(update_insp, [primary_rest_id, ids])
                self.conn.commit()

        return 200


    def find_similarity(self, dirty_r, r, name_weight=0.45, address_weight=0.4,
                        city_weight=0.09, state_weight=0.06):
        '''
        Find similarities for all components of a dirty restaurant (dirty_r)
        compared to a restaurant (r).

        Output:
            similarity_scores (a dict): dictionary mapping attribute keys to 
            scores.
        '''

        d_id = dirty_r["id"]
        a_id = r["id"]
        d_name = dirty_r["name"]
        a_name = r["name"]
        d_address = dirty_r["address"]
        a_address = r["address"]
        d_city = dirty_r["city"]
        a_city = r["city"]
        d_state = dirty_r["state"]
        a_state = r["state"]

        if d_id != a_id: # Don't match a restaurant to itself
            # Get name similarity score 
            jarowinky = JaroWinkler()
            name_sim = jarowinky.similarity(d_name, a_name)
            name_score = name_sim * name_weight
            # Get address similarity score
            address_alg = textdistance.algorithms
            address_sim = address_alg.jaccard.normalized_similarity(d_address, a_address)
            address_score = address_sim * address_weight
            # Get city similarity score
            city_alg = textdistance.algorithms
            city_sim = city_alg.levenshtein.normalized_similarity(d_city, a_city)
            city_score = city_sim * city_weight 
            # Get state similarity score
            if d_state == a_state:
                state_sim = 1.0
            else:
                state_sim = 0.0
            state_score = state_sim * state_weight
            # Get total similarity score
            total_score = name_score + address_score + city_score + state_score

            return total_score
        

    def find_all_rest_by_insp(self, inspection_id):
        '''
        Given an inspection_id, returns the primary restaurant for the inspection, 
        a list of all linked restaurants, and a list of all ids of associated/linked 
        restaurants.
        '''
        c = self.conn.cursor()
        query1 = "SELECT r.id, name, facility_type, address, city, state, zip, latitude,\
                  longitude, clean FROM ri_restaurants r JOIN ri_inspections i ON\
                   r.id = i.restaurant_id WHERE i.id = ? ORDER BY r.id;"
        c.execute(query1, [inspection_id])
        restaurant = to_json_list(c)[0]

        query2 = "SELECT r.id, name, facility_type, address, city, state, zip, latitude,\
                 longitude, clean FROM ri_restaurants r JOIN ri_inspections i ON r.id = \
                 i.restaurant_id JOIN ri_linked l ON l.primary_rest_id = r.id WHERE i.id = ?\
                 ORDER BY r.id;"
        c.execute(query2, [inspection_id])
        linked = to_json_list(c)


        query = "SELECT  original_rest_id FROM ri_restaurants r JOIN ri_inspections i\
                 ON r.id = i.restaurant_id  JOIN ri_linked l ON l.primary_rest_id = r.id\
                 WHERE i.id = ? ORDER BY original_rest_id;"
        c.execute(query, [inspection_id])
        lst_ids = to_json_list(c)
        matched_ids = [sorted(list(item.values())) for item in lst_ids]

        return restaurant, linked, matched_ids

        

    # Simple example of how to execute a query against the DB.
    # Again NEVER do this, you should only execute parameterized query
    # See https://docs.python.org/3/library/sqlite3.html#sqlite3.Cursor.execute
    # This is the qmark style:
    # cur.execute("insert into people values (?, ?)", (who, age))
    # And this is the named style:
    # cur.execute("select * from people where name_last=:who and age=:age", {"who": who, "age": age})
    def run_query(self, query):
        c = self.conn.cursor()
        c.execute(query)
        res =to_json_list(c)
        self.conn.commit()
        return res