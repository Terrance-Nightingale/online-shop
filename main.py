from flask import Flask, jsonify, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy()
db.init_app(app)

Bootstrap5(app)


# User Config
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(50), unique=False, nullable=False)
    # orders = order ids (refer to orders db)


# Item Config
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    price = db.Column(db.Integer, unique=False, nullable=False)
    stock = db.Column(db.Integer, unique=False, nullable=False)


# Order Config
class Order(db.Model):
    order_number = db.Column(db.Integer, primary_key=True)
    # user_id = user.id (refer to User db)
    # items = dictionary of item ids and quantities (refer to items)



with app.app_context():
    db.create_all()


@app.route("/")
def home():
    status = False
    identity = False
    # db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
    # items = [cafe for cafe in db_cafes]
    return render_template("index.html", logged_in=status, manager=identity)


@app.route("/login")
def login():
    status = False
    identity = False
    return render_template("login.html", logged_in=status, manager=identity)


# @app.route("/syrups")
# def syrup():
#     # db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
#     # items = [item for item in db_items]
#     return render_template("syrups.html")
# # Add salesfront=items as a **kwarg


if __name__ == '__main__':
    app.run(debug=True)
