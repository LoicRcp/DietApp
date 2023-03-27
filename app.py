import logging
from logging import INFO
from logging.handlers import RotatingFileHandler
from os import path
import re

import requests
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
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS products(
barcode INTEGER PRIMARY KEY UNIQUE,
name TEXT, 
quantity INTEGER, 
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

def productToJson(product):
    return {
        "barcode": product[0],
        "name": product[1],
        "quantity": product[2],
        "measure": product[3],
        "calories": product[4],
        "fats": product[5],
        "saturated_fats": product[6],
        "carbohydrates": product[7],
        "sugars": product[8],
        "proteins": product[9],
        "salt": product[10],
        "fiber": product[11]
    }
def checkExistanceInDatabase(barcode):
    cursor.execute("SELECT * FROM products WHERE barcode = ?", (barcode,))
    return cursor.fetchone()

def addProductInDatabase(product):
    cursor.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", tuple(product))
    conn.commit()
def getProductFromExternalApi(barcode):
    productJson = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json").json()
    if productJson["status"] == 1:
        try:
            temp = re.compile("([0-9]+)([a-zA-Z]+)")
            quantity = productJson.get("product").get("quantity")
            quantity = temp.match(quantity).groups()
            product = [
            productJson.get("code"),
            productJson.get("product").get("product_name"),
            quantity[0],
            quantity[1],
            productJson.get("product").get("nutriments").get("energy-kcal_100g"),
            productJson.get("product").get("nutriments").get("fat_100g"),
            productJson.get("product").get("nutriments").get("saturated-fat_100g"),
            productJson.get("product").get("nutriments").get("carbohydrates_100g"),
            productJson.get("product").get("nutriments").get("sugars_100g"),
            productJson.get("product").get("nutriments").get("proteins_100g"),
            productJson.get("product").get("nutriments").get("salt_100g"),
            productJson.get("product").get("nutriments").get("fiber_100g")]
            return product
        except Exception as e:
            print(e)
    else:
        return None



@app.route('/scan-barcode', methods=['POST'])
def scan_barcode():
    barcode = request.get_json()
    product = checkExistanceInDatabase(int(barcode))
    if product:
        jsonToReturn = {"product": productToJson(product), "fromDb": True, "status": -1,
                        'code': product[0], "errorMess": None}
        return jsonToReturn
    else:
        product = getProductFromExternalApi(barcode)
        if product == None:
            jsonToReturn = {
                "status": 1,
            }
            return jsonToReturn
        else:
            errorMess = ""
            if None in product:
                ## C'est DEGEULASSE mais j'ai rien de mieux en tête qui prendrait pas une plombe
                if product[1] == None:
                    errorMess += "Name, "
                if product[2] == None:
                    errorMess += "Quantity, "
                if product[3] == None:
                    errorMess += "Measure, "
                if product[4] == None:
                    errorMess += "Calories, "
                if product[5] == None:
                    errorMess += "Fats, "
                if product[6] == None:
                    errorMess += "Saturated fats, "
                if product[7] == None:
                    errorMess += "Carbohydrates, "
                if product[8] == None:
                    errorMess += "Sugars, "
                if product[9] == None:
                    errorMess += "Proteins, "
                if product[10] == None:
                    errorMess += "Salt, "
                if product[11] == None:
                    errorMess += "Fiber, "
            addProductInDatabase(product)
            jsonToReturn = {"product": productToJson(product), "fromDb": False, "status": 0 if errorMess != None else -1, 'code': product[0], "errorMess": errorMess}
            return jsonToReturn

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    return render_template('scan.html')
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
