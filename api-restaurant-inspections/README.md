# RestInsp - Basic Web Service Endpoints

This project sets up basic endpoints of web service for a music service "RestInsp", which manages (altered) data for food inpsections from the city of Chicago. Note the project uses the restaurant but many locations in the dataset are not actually restaurants, I treat all locations as restaurants for simplicity.

These endpoints will receive http POST requests to store data and http GET requests to read data. The data is sent and received as [JSON](https://www.w3schools.com/js/js_json_intro.asp). JSON is a simple textual data format, that can store objects (e.g. dictionary or map), a list, or primitive values. The API web service will respond to http requests with a JSON response body and a [numeric http response code](https://www.restapitutorial.com/httpstatuscodes.html) that indicates a valid request (200), that something was created (201), an unknown error occurred (400), or that a lookup did not find the requested data (404).

This project is a REST-ful set up, where operations like create and read data get mapped to a URL. At its core, REST is a simple http APIs to create, read, update, and delete data using stateless web requests. 

The components for the project include:

 - `server/server.py` contains the code for the web/http server. All requests made to the server get mapped to a function in this file (an endpoint). These functions get arguments (either from the [URL](https://developer.mozilla.org/en-US/docs/Learn/Common_questions/What_is_a_URL) or from data that was sent as the "body" of a post request). Most endpoints will in turn make a call to the underlying database. 
 - `server/db.py` is the data access layer. This class will hold the connection to the database (sqlite3) and provide functions that insert and read data. Most of the work is in this file. 
 - `server/errors.py` defines some common exceptions/errors.
 - `client/client.py` is the client/driver for testing the application. This program reads a workload file that specifies a list of files, that each give an endpoint, an expected http response code, an optional payload (data to send), and an option response body to verify against. Y

## Technologies used

-  [Flask](https://flask.palletsprojects.com/en/2.0.x/quickstart/) is a lightweight and popular web framework written in Python. Flask provides an easy way to map http requests to a function and return http/html/json responses.
-  [SQLite](https://www.sqlite.org/index.html) is an embedded relational database.  It does not have the full set of features as something like PostgreSQL but is very easy to use and install. I use the [sqlite3 database driver](https://docs.python.org/3/library/sqlite3.html) to connect and interact with the DBMS via Python.  


## Web/html wrapper
A simple web (html) interface to some of the underlying JSON REST endpoints is provided. This is to allow testing the end points in a browser, as opposed to sending JSON http requests via program like CURL or Python. After starting the server, visit http://localhost:30235/ and see the top menu links to the web wrappers. In app.py these are all prefixed with /web and as you can see in the code, most of these just take the input from the form and call the REST JSON endpoint and return the results. The exception to this is the query endpoint which will let you run an arbitrary SQL statement against the database. 
