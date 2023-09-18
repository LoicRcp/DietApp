import json
import logging
import os
import sys
from logging import INFO
from logging.handlers import RotatingFileHandler
from os import path
import re

import requests
from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

## Initialize the loggers

logFile = f"{path.dirname(path.realpath(__file__))}/dietApp.log"

logHandler = RotatingFileHandler(logFile, mode="a", maxBytes=200 * 1024 * 1024, backupCount=1, encoding="utf-8")
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
load_dotenv('key.env')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

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


def deleteProductFromDatabase(barcode):
    try:
        cursor.execute("DELETE FROM products WHERE barcode = ?", (barcode,))
        conn.commit()
        return None
    except Exception as e:
        return e


def addProductInDatabase(product):
    cursor.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", tuple(product))
    conn.commit()


def getProductFromExternalApi(barcode):
    productJson = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json").json()
    if productJson["status"] == 1:
        try:
            temp = re.compile("([0-9]+)([a-zA-Z]+)")
            quantity = productJson.get("product").get("quantity").replace(" ", "")
            quantity = temp.match(quantity).groups()
            product = [
                productJson.get("code"),
                productJson.get("product").get("product_name_fr") + " - " + productJson.get("product").get("brands"),
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
            app_log.error(f"Error while getting product from external API: {e}")
            app_log.error("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
    else:
        return None



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mail = request.form['email']
        password = generate_password_hash(request.form['password'])
        username = request.form['username']

        cur = conn.cursor()
        cur.execute("INSERT INTO users(email, username, password_hash) VALUES(?, ?, ?)", (mail, username,  password))
        conn.commit()
        cur.close()

        session['logged_in'] = True
        session['user_email'] = mail
        session['username'] = username

        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and (session.get('logged_in') is None or session.get('logged_in') is False):
        mail = request.form['email']

        password = request.form['password']
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (mail,))
        user = cur.fetchone()
        cur.close()
        if user:
            if check_password_hash(user[3], password):
                session['logged_in'] = True
                session['user_email'] = mail
                session['username'] = user[1]
                return redirect(url_for('index'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
        else:
            error = 'User not found'
            return render_template('login.html', error=error)
    return render_template('login.html')
@app.route('/delete-product', methods=['POST'])
def delete_product():
    barcode = request.get_json()
    response = deleteProductFromDatabase(barcode)
    if response == None:
        return {"status": 1}
    else:
        return {"status": response}


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
            jsonToReturn = {"product": productToJson(product), "fromDb": False, "status": 0 if errorMess != "" else -1,
                            'code': product[0], "errorMess": errorMess}
            return jsonToReturn


def getAllProductsFromDatabase():
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return products


@app.route('/scan', methods=['GET', 'POST'])
def scan():
    return render_template('scan.html')


@app.route("/", methods=["GET", "POST"])
def index():
    items = getAllProductsFromDatabase()
    items = [productToJson(item) for item in items]
    return render_template("index.html", items=items)


@app.route('/get-meal-plan', methods=['POST'])
def my_flask_route_2():
    data = request.get_json()

    responseData = []
    for i in range(len(data) - 1):
        responseData.append(productToJson(checkExistanceInDatabase(data[i]['id'])))
    return json.dumps(responseData)

@app.before_request
def before_request():
    if not session.get('logged_in') and request.endpoint != 'login' and request.endpoint != 'register':
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
