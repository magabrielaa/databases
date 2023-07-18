import json  # For reading and writing results
from flask import current_app, g, Flask, flash, jsonify, redirect, render_template, request, session, Response
import requests  # Used for web/html wrapper
import argparse  # Used for getting arguments for creating server
import sqlite3  # Our DB
import logging  # Logging Library
from db import DB  # our custom data access layer
from errors import KeyNotFound, BadRequest, InvalidUsage # Custom Error types
import string  # for ngram generation


# Configure application
app = Flask(__name__)

app.config['JSON_SORT_KEYS'] = False

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Variable to track transaction size
app.config["TRANS_SIZE"] = 1

# Counter variable to keep track of the number of times inspection is called
app.config["INSP_COUNTER"] = 0

# Needed to flash messages
app.secret_key = b'mEw6%7BPK'

# path to database
DATABASE = 'insp.db'

def get_db_conn():
    """ 
    gets connection to database
    """
    if "_database" not in app.config:
        app.config["_database"] = sqlite3.connect(DATABASE)
        return app.config["_database"] 
    else:
        return app.config["_database"] 

# default path
@app.route('/')
def home():
    return render_template("home.html")

# Hello, World
@app.route("/hello", methods=["GET"])
def hello():
    return "Hello, World!"

@app.route("/create", methods=["GET"])
@app.route("/reset", methods=["GET"])
def create():
    logging.debug("Running Create/Reset")
    db = DB(get_db_conn())
    db.create_script()
    return {"message": "created"}

@app.route("/seed", methods=["GET"])
def seed():
    db = DB(get_db_conn())
    db.seed_data()
    return {"message": "seeded"}


@app.route("/restaurants/<int:restaurant_id>", methods=["GET"])
def find_restaurant(restaurant_id):
    """
    Returns a restaurant and all of its associated inspections.
    """
    logging.info('Find restaurant request received')
    db = DB(get_db_conn())

    try:
        restaurant = db.find_restaurant(restaurant_id)[0]
        res = db.find_inspections(restaurant_id)
        restaurant["inspections"] = res
        return restaurant, 200
    except KeyError as e:
        logging.error(e)
        raise InvalidUsage(message=str(e), status_code=404) 


@app.route("/restaurants/by-inspection/<inspection_id>", methods=["GET"])
def find_restaurant_by_inspection_id(inspection_id):
    """
    Returns a restaurant associated with a given inspection.
    """
    logging.info('Find restaurant by inspection request received')
    db = DB(get_db_conn())

    try:
        res = db.find_rest_by_inspection(inspection_id)
        return res[0], 200
    except KeyError as e:
        logging.error(e)
        raise InvalidUsage(message=str(e), status_code=404) 
    

@app.route("/inspections", methods=["POST"])
def load_inspection():
    """
    Loads a new inspection (and possibly a new restaurant) into the database.
    Note that if db or server throws a KeyNotFound, BadRequest or InvalidUsage
    error the web framework will automatically generate the right error
    response.
    """
    postbody = request.json

    if not postbody:
        logging.error("No post body")
        return Response(status=400)

    # Increment the inspection counter 
    app.config["INSP_COUNTER"] += 1

    if (postbody["inspection_id"] == "" or postbody["name"] == "" 
        or postbody["address"] == ""):
        logging.info('Bad request with required attributes missing')
        raise BadRequest(message=str(e), status_code=400) 

    rest_keys = ["name", "facility_type", "address", "city", "state", "zip",
                 "latitude", "longitude", "clean"]
    restaurant = {key:value for key, value in postbody.items()
                  if key in rest_keys}
    insp_keys = ["inspection_id", "risk", "date", "inspection_type",
                 "results", "violations", "restaurant_id"]
    inspection = {key:value for key, value in postbody.items()
                  if key in insp_keys}

    db = DB(get_db_conn())
    try:
        resp = db.add_inspection_for_restaurant(inspection, restaurant)
        if app.config["INSP_COUNTER"] == app.config["TRANS_SIZE"]:
            commit_txn()
            logging.info("Committed transaction")
        return {"restaurant_id": resp[0]}, resp[1]
    except Exception as e:
        abort_txn()
        logging.info('Transaction aborted %s' % e)
        return Response(status=400)


@app.route("/txn/<int:txnsize>", methods=["GET"])
def set_transaction_size(txnsize):
    # TODO milestone 2
    commit_txn()
    app.config["TRANS_SIZE"] = txnsize
    return "Transaction size set"


@app.route("/commit")
def commit_txn():
    logging.info("Committing active transactions")
    db = DB(get_db_conn())
    db.conn.commit()
    app.config["INSP_COUNTER"] = 0 
    return "Active transactions, if any, committed"


@app.route("/abort")
def abort_txn():
    logging.info("Aborting/rolling back active transactions")
    # TODO milestone 2
    db = DB(get_db_conn())
    db.conn.rollback()
    app.config["INSP_COUNTER"] = 0 
    return "Active transactions, if any, aborted"


@app.route("/count")
def count_insp():
    logging.info("Counting Inspections")
    db = DB(get_db_conn())
    res = db.total_inspections()
    return str(res[0]['COUNT (*)']), 200


def ngrams(tweet, n):
    """
    A helper function that will take text and split it into n-grams based on
    spaces.
    """
    single_word = tweet.translate(
        str.maketrans('', '', string.punctuation)).split()
    output = []
    for i in range(len(single_word) - n + 1):
        output.append(' '.join(single_word[i:i + n]))
    return output


@app.route("/tweet", methods=["POST"])
def tweet():
    logging.info("Checking Tweet")
    postbody = request.json

    ngs = []
    for i in range (1,5):
        ngs.extend(ngrams(postbody["text"], i))

    lat = postbody["lat"]
    long = postbody["long"]
    tkey = postbody["key"]

    if not postbody:
        logging.error("No post body")
        return Response(status=400)

    db = DB(get_db_conn())
    try:
        res = db.tweet_match(ngs, lat, long, tkey)
        commit_txn()
        return jsonify(res), 201
    except KeyError as e:
        logging.error(e)
        raise InvalidUsage(message=str(e), status_code=404) 


@app.route("/tweets/<int:restaurant_id>", methods=["GET"])
def find_restaurant_tweets(restaurant_id):
    """
    Returns a restaurant's associated tweets (tkey and match).
    """
    db = DB(get_db_conn())
    # TODO milestone 2
    try:
        res = db.find_tweets(restaurant_id)
        return jsonify(res), 200
    except KeyError as e:
        logging.error(e)
        raise InvalidUsage(message=str(e), status_code=404) 


@app.route("/clean")
def clean():
    """
    Cleans up restaurant records and links together restaurants that matched.
    """

    logging.info("Cleaning Restaurants")

    db = DB(get_db_conn())
    # TODO milestone 3
    try:
        if app.config['scaling'] is True:
            res_scale = db.block_records(True)
            return jsonify(res_scale)
        else:
            res = db.block_records(False)
            return jsonify(res)   
    except KeyError as e:
        logging.error(e)
        raise InvalidUsage(message=str(e), status_code=404) 


@app.route("/restaurants/all-by-inspection/<inspection_id>", methods=["GET"])
def find_all_restaurants_by_inspection_id(inspection_id):
    """
    Given an inspection id, returns all linked restaurants associated
    with it.
    """
    logging.info("Getting linked restaurants by inspection")
    db = DB(get_db_conn())
    try:
        restaurant, linked, matched_ids = db.find_all_rest_by_insp(inspection_id)
        return {"primary": restaurant, "linked": linked, "ids": matched_ids}, 200
    except KeyError as e:
        logging.error(e)
        raise InvalidUsage(message=str(e), status_code=404) 

# -----------------
# Web APIs
# These simply wrap requests from the website/browser and
# invoke the underlying REST / JSON API.
# -------------------

@app.route('/web/query', methods=["GET", "POST"])
def query():
    """
    runs pasted/entered query
    """
    data = None
    if request.method == "POST":
        qry = request.form.get("query")
        # Ensure query was submitted

        # get DB class with new connection
        db = DB(get_db_conn())

        # note DO NOT EVER DO THIS NORMALLY (run SQL from a client/web directly)
        # https://xkcd.com/327/
        try:
            res = db.run_query(str(qry))
        except sqlite3.Error as e:
            logging.error(e)
            return render_template("error.html", errmsg=str(e), errcode=400)

        data = res
    return render_template("query.html", data=data)


@app.route('/web/post_data', methods=["GET", "POST"])
def post_song_web():
    """
    runs simple post request
    """
    data = None
    if request.method == "POST":
        parameter = request.form.get("path")
        if parameter is None or parameter.strip() == "":
            flash("Must set key")
            return render_template("post_data.html", data=data)

        get_url = "%s/%s" % (app.config['addr'], parameter)
        logging.debug("Making request to %s" % get_url)
        # grab the response

        j = json.loads(request.form.get("json_data").strip())
        logging.debug("Json from form: %s" % j)
        r = requests.post(get_url, json=j)
        if r.status_code >= 400:
            logging.error("Error.  %s  Body: %s" % (r, r.content))
            return render_template("error.html", errmsg=r.json(), errcode=r.status_code)

        else:
            flash("Ran post command")
        return render_template("post_data.html", data=None)
    return render_template("post_data.html", data=None)


@app.route('/web/create', methods=["GET"])
def create_web():
    get_url = "%s/create" % app.config['addr']
    logging.debug("Making request to %s" % get_url)
    # grab the response
    try:
        r = requests.get(get_url)
        if r.status_code >= 400:
            logging.error("Error.  %s  Body: %s" % (r, r.content))
            return render_template("error.html", errmsg=r.json(), errcode=r.status_code)
        else:
            flash("Ran create command")
            data = r.json()
    except Exception as e:
        logging.error("%s\n$%s %s" % (e, r, r.content))
        return render_template("error.html", errmsg=e, errcode=400)

    return render_template("home.html", data=data)


@app.route('/web/restaurants', methods=["GET", "POST"])
def rest_landing():
    data = None
    if request.method == "POST":
        path = request.form.get("path")
        # Ensure path was submitted

        parameter = request.form.get("parameter")
        if parameter is None or parameter.strip() == "":
            flash("Must set key")
            return render_template("albums.html", data=data)

        get_url = ("%s/restaurants/" % app.config['addr']) + path + parameter
        # grab the response
        logging.debug("Making call to %s" % get_url)
        r = requests.get(get_url)
        if r.status_code >= 400:
            logging.error("Error.  %s  Body: %s" % (r, r.content))
            return render_template("error.html", errmsg=r.json(), errcode=r.status_code)
        else:
            try:
                data = r.json()
                logging.debug("Web Rest got : %s" % data)
            except Exception as e:
                logging.error("%s\n$%s %s" % (e, r, r.content))
    return render_template("restaurants.html", data=data)


# -----------------
# Utilities / Errors
# -------------------

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.errorhandler(KeyNotFound)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = 404
    return response


@app.errorhandler(BadRequest)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = 404
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        help="Server hostname (default 127.0.0.1)",
        default="127.0.0.1"
    )
    parser.add_argument(
        "-p", "--port",
        help="Server port (default 30235)",
        default=30235,
        type=int
    )
    parser.add_argument(
        "-s", "--scaling",
        help="Enable large scale cleaning (MS4)",
        default=False,
        action="store_true"
    )
    parser.add_argument(
        "-l", "--log",
        help="Set the log level (debug,info,warning,error)",
        default="warning",
        choices=['debug', 'info', 'warning', 'error']
    )

    # The format for our logger
    log_fmt = '%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s'
    
    # Create the parser argument object
    args = parser.parse_args()
    if args.log == 'debug':
        logging.basicConfig(
            format=log_fmt, level=logging.DEBUG)
        logging.debug("Logging level set to debug")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.DEBUG)
    elif args.log == 'info':
        logging.basicConfig(
            format=log_fmt, level=logging.INFO)
        logging.info("Logging level set to info")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.INFO)
    elif args.log == 'warning':
        logging.basicConfig(
            format=log_fmt, level=logging.WARNING)
        logging.warning("Logging level set to warning")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
    elif args.log == 'error':
        logging.basicConfig(
            format=log_fmt, level=logging.ERROR)
        logging.error("Logging level set to error")
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    # Store the address for the web app
    app.config['addr'] = "http://%s:%s" % (args.host, args.port)

    # set scale
    if args.scaling:
        app.config['scaling'] = True
    else:
        app.config['scaling'] = False
    logging.info("Scaling set to %s" % app.config['scaling'])
    logging.info("Starting Inspection Service")
    app.run(host=args.host, port=args.port, threaded=False, debug=True)
