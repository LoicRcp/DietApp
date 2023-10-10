import datetime
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

#DATABASE STRUCTURE
"""
create table products
(
    barcode        INTEGER
        primary key,
    name           TEXT,
    portion        INTEGER,
    measure        TEXT,
    calories       INTEGER,
    fats           INTEGER,
    saturated_fats INTEGER,
    carbohydrates  INTEGER,
    sugars         INTEGER,
    proteins       INTEGER,
    salt           INTEGER,
    fiber          INTEGER
);

create table users
(
    id            INTEGER      not null
        primary key autoincrement,
    username      VARCHAR(255) not null,
    email         VARCHAR(255) not null
        unique,
    password_hash TEXT         not null
);

create table virtual_fridge
(
    virtual_fridge_id integer not null
        constraint virtual_fridge_pk
            primary key,
    user_id           integer not null
        constraint user_id
            references users
);

create table fridge
(
    content_id integer not null
        constraint content_id
            primary key autoincrement,
    fridge_id  integer not null
        constraint fridge_id
            references virtual_fridge,
    food_id    integer not null
        constraint food_id
            references products,
    quantity   REAL
);
"""


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
        "portion_quantity": product[2],
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
            temp = re.compile("([0-9]+)([a-zA-ZœŒ]+)")
            quantity = productJson.get("product").get("quantity").replace(" ", "")
            quantity = temp.match(quantity).groups()

            def extract_nutrient(productJson, nutrient_name):
                nutriments = productJson.get("product").get("nutriments")
                estimated_nutriments = productJson.get("product").get("nutriments_estimated")
                return nutriments.get(nutrient_name) if nutriments.get(
                    nutrient_name) is not None else estimated_nutriments.get(nutrient_name)

            product = [
                productJson.get("code"),
                productJson.get("product").get("generic_name_fr") + " - " + productJson.get("product").get("brands"),
                quantity[0],
                quantity[1],

                extract_nutrient(productJson, "energy-kcal_100g"),
                extract_nutrient(productJson, "fat_100g"),
                extract_nutrient(productJson, "saturated-fat_100g"),
                extract_nutrient(productJson, "carbohydrates_100g"),
                extract_nutrient(productJson, "sugars_100g"),
                extract_nutrient(productJson, "proteins_100g"),
                extract_nutrient(productJson, "salt_100g"),
                extract_nutrient(productJson, "fiber_100g")
            ]
            return product
        except Exception as e:
            app_log.error(f"Error while getting product from external API: {e}")
            app_log.error("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            raise Exception(f"Error while getting product from external API {e}")
    else:
        return None

def createVirtualFridge(user_id):
    cursor.execute("INSERT INTO virtual_fridge(user_id) VALUES (?)", (user_id,))
    conn.commit()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and (session.get('logged_in') is None or session.get('logged_in') is False):
        mail = request.form['email']
        password = generate_password_hash(request.form['password'])
        username = request.form['username']

        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users(email, username, password_hash) VALUES(?, ?, ?)", (mail, username,  password))
            conn.commit()
            cur.close()
        except Exception as e:
            return render_template('register.html', error=str(e))

        createVirtualFridge(getUserId(mail))
        session['logged_in'] = True
        session['user_email'] = mail
        session['username'] = username

        return redirect(url_for('index'))
    elif request.method == 'GET' and (session.get('logged_in') is True):
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
    elif request.method == 'GET' and (session.get('logged_in') is True):
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
def logout():
    if session:
        session.clear()
    return redirect(url_for('login'))

@app.route('/delete-product', methods=['POST'])
def delete_product():
    barcode = request.get_json()
    response = deleteProductFromDatabase(barcode)
    if response == None:
        return {"status": 1}
    else:
        return {"status": response}

def getUserId(email):
    result = cursor.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
    return result

def getUserFridge(userId):
    result = cursor.execute("SELECT virtual_fridge_id FROM virtual_fridge WHERE user_id = ?", (userId,)).fetchone()[0]
    return result

def productInUserFridge(barcode):
    userId = getUserId(session['user_email'])
    userFridgeId = getUserFridge(userId)
    product = cursor.execute("SELECT quantity FROM fridge WHERE fridge_id = ? AND food_id = ?", (userFridgeId, barcode))
    return product.fetchone()

@app.route('/add-to-fridge', methods=['POST'])
def add_to_fridge():
    barcode = request.get_json()
    product = checkExistanceInDatabase(int(barcode))
    fridgeId = getUserFridge(getUserId(session['user_email']))
    if product:
        if productInUserFridge(int(barcode)):
            cursor.execute("UPDATE fridge SET quantity = quantity + 1 WHERE food_id = ? AND fridge_id = ?", (barcode, fridgeId))
        else:
            cursor.execute("INSERT INTO fridge (fridge_id, food_id, quantity) VALUES (?, ?, ?)", (fridgeId, barcode, 1))
        conn.commit()
        return {"status": 1}
    else:
        return {"status": 0}

@app.route('/update-fridge', methods=['POST'])
def update_fridge():
    data = request.get_json()
    fridgeId = getUserFridge(getUserId(session['user_email']))
    try:
        for item in data:
            cursor.execute("UPDATE fridge SET quantity = ? WHERE food_id = ? AND fridge_id = ?", (item['number'], item['id'], fridgeId))
        conn.commit()
    except Exception as e:
        return {"status": str(e)}

    return {"status": 1}


@app.route('/scan-barcode', methods=['POST'])
def scan_barcode():
    barcode = request.get_json()
    product = checkExistanceInDatabase(int(barcode))
    if product:
        jsonToReturn = {"product": productToJson(product), "fromDb": True, "status": -1,
                        'code': product[0], "errorMess": None}
        return jsonToReturn
    else:
        try:
            product = getProductFromExternalApi(barcode)
            if product == None:
                jsonToReturn = {
                    "status": 1,
                }
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
        except Exception:
            jsonToReturn = {
                "status": 2,
                "timestamp": datetime.datetime.now().timestamp(),
            }
        return jsonToReturn


def getAllProductsFromDatabase():
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return products

def getUserProductsFromDatabase(email):
    userFridge = getUserFridge(getUserId(email))
    cursor.execute("SELECT p.*, f.quantity AS qty FROM products p JOIN fridge f on p.barcode = f.food_id WHERE f.fridge_id = ?", (userFridge,))
    products = cursor.fetchall()
    return products

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    return render_template('scan.html')

def process_and_sort_fridge_items(user_email):
    fridge_items = getUserProductsFromDatabase(user_email)
    fridge_items = [(item[:-1], item[-1]) for item in fridge_items]
    fridge_items = [(productToJson(item[0]), item[1]) for item in fridge_items]
    fridge_items.sort(key=lambda x: x[1], reverse=True)
    return fridge_items
@app.route('/fridge', methods=['GET'])
def fridge():
    return render_template('fridge.html', items=process_and_sort_fridge_items(session['user_email']))

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html", items=process_and_sort_fridge_items(session['user_email']))


@app.route('/get-meal-plan', methods=['POST'])
def my_flask_route_2():
    data = request.get_json()
    responseData = []
    for i in range(len(data) - 1):
        productJson = productToJson(checkExistanceInDatabase(data[i]['id']))
        productJson.pop('fats', None)
        productJson.pop('saturated_fats', None)
        productJson.pop('carbohydrates', None)
        productJson.pop('sugars', None)
        productJson.pop('salt', None)
        productJson.pop('fiber', None)
        responseData.append(productJson)

    responseData.append({"CaloriesGoal": 1000})
    responseData.append({"ProteinsGoal": 70})

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(responseData, f, ensure_ascii=False, indent=4)

    return json.dumps(responseData)

@app.before_request
def before_request():
    if not session.get('logged_in') and request.endpoint != 'login' and request.endpoint != 'register':
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)




#TODO: Faire la page pour gérer son frigo (afficher les produits DANS le frigo en priorité, puis tout les produits déjà ajouté par l'utilisateur)
#TODO: Ajouter un moyen de faire des soustractions/ajouts de quantité de produits (dire j'ai pris/ajouté X g d'un produit)
#TODO: Ajouter un produit au frigo
#TODO: Update l'index pour afficher les produits présents DANS le frigo uniquement
#TODO: Envoyer les données du frigo a gpt-4
#TODO: Améliorer le prompt
#TODO: Faire une page pour afficher le meal plan, les étapes et les commentaires. Calculer les calories et les protéines.
#TODO: Si la recette est validé par le user, update la DB pour enlever les produits utilisés
#TODO: FIX les problèmes avec les ingrédiants ne se comptant pas en grammes (ex: 1 oeuf)


"""
Act as a panel of 3 disagreeable Nutritionnal expert. You will analyse the data I send you in the JSON format, then formulate an answer in the format detailled below.

Context: You are part of an application aimed to provide users recipe according to their needed nutrionnal value in a meal, while taking in accounts what they have in their fridge. The fridge content will be provided in a JSON format, that will be the ingrediants you can use in your recipe. There will also be the user constraints.  

System Constraints:
- The meal need to be pleasent/decent to eat, not overly complicated to make.
- The calorie/proteins can be off by only 10%
- You can use a fraction of the ingrediant quantity to meet the constraints. 
- Try to avoid using disproportionate amounts of an ingrediants, it must be coherent.
- Try to avoid leaving small amount of an ingrediant (ex: avoid using 90% of ingrediant leaving it to 10%) 


What is a recipe: The recipe is a json formatted text, with the ingrediants and the quantity needed for the meal. There is a section dedicated to any comments you need to make. That can be cooking instruction, or anything else you consider important.

The output format will be the following:

{
    "ingrediants": [
        {
            "barcode": 123456789,
            "quantity": 100
        },
        ...
        ],
    "recipe_steps": [
        "step1": "Do this",
        "step2": "Do that",
        ...
        ],
    "comments": [
        "This is a comment",
        "This is another comment"
        ...
        ]
"""
