import cv2
from pyzbar import pyzbar
from flask import Flask, render_template, request

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
