import os
from turtle import back
from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, render_template, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

# Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user):
    return User.get(user)

# User Config
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(50), unique=False, nullable=False)
    clearance = db.Column(db.Boolean, unique=False, nullable=False)
    orders = relationship("Order", back_populates="customer")


# Item Config
class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    price = db.Column(db.Float, unique=False, nullable=False)
    volume = db.Column(db.Float, unique=False, nullable=True)
    stock = db.Column(db.Integer, unique=False, nullable=False)


# Ordered Item Config
class OrderItem(UserMixin, Item, db.Model):
    __tablename__ = "ordered-items"
    id = db.Column(db.Integer, db.ForeignKey("items.id"), primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    parent_order = relationship("Order", back_populates="items")
    quantity = db.Column(db.Integer, unique=False, nullable=False)


# Order Config
class Order(UserMixin, db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="parent_order")


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


# @app.route("/add-item")
# def login():
#     status = False
#     identity = False
#     return render_template("login.html", logged_in=status, manager=identity)


# @app.route("/syrups")
# def syrup():
#     # db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
#     # items = [item for item in db_items]
#     return render_template("syrups.html")
# # Add salesfront=items as a **kwarg


if __name__ == '__main__':
    app.run(debug=True)
