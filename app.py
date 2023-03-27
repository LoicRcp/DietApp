import logging
from logging import INFO
from logging.handlers import RotatingFileHandler
from os import path

import cv2
from pyzbar import pyzbar
from flask import Flask, render_template, request
import sqlite3


## Initialize the loggers

logFile = f"{path.dirname(path.realpath(__file__))}/dietApp.log"

logHandler = RotatingFileHandler(logFile, mode="a", maxBytes=200*1024*1024, backupCount=1, encoding="utf-8")
logHandler.setLevel(INFO)
logHandler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(funcName)s(%(lineno)d) - %(message)s"))

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)
if not app_log.hasHandlers():
    app_log.addHandler(logHandler)


## Initialize the Database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS products(
barcode INTEGER PRIMARY KEY,
name TEXT, 
portion INTEGER, 
measure TEXT,
calories INTEGER,
fats INTEGER,
saturated_fats INTEGER,
carbohydrates INTEGER,
sugars INTEGER,
proteins INTEGER,
salt INTEGER,
fiber INTEGER)""")

conn.commit()
## Initialize the Flask app

app = Flask(__name__)

# sample data
items = [
    {"id": '000', "name": "Chicken breast", "calories": 200, "proteins": 30},
    {"id": '001', "name": "Salmon fillet", "calories": 250, "proteins": 25},
    {"id": '002', "name": "Spinach", "calories": 10, "proteins": 1},
    {"id": '003', "name": "Broccoli", "calories": 20, "proteins": 2},
    {"id": '004', "name": "Brown rice", "calories": 150, "proteins": 5},
    {"id": '005', "name": "Quinoa", "calories": 200, "proteins": 8},
    {"id": '006', "name": "Sweet potato", "calories": 100, "proteins": 2},
    {"id": '007', "name": "Banana", "calories": 80, "proteins": 1},
]

@app.route('/scan', methods=['GET', 'POST'])
def scan():

    return render_template('scan.html')


@app.route('/scan-barcode', methods=['POST'])
def scan_barcode():
    # Read the image
    print("Scanning barcode...")
    print(request.files)
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html", items=items)


@app.route('/my-flask-route', methods=['POST'])
def my_flask_route_2():
    # Retrieve data from the database or wherever it's stored
    data = request.get_json()
    print(data)
    # Render the template with the data
    return data

if __name__ == '__main__':
    app.run(debug=True)
