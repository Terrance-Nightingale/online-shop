import os
from forms import *
from turtle import back
from dotenv import load_dotenv
from flask import Flask, abort, flash, render_template, redirect, url_for, request
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
def load_user(user_id):
    return db.get_or_404(User, user_id)


def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return wrapper


# User Config
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(50), unique=False, nullable=False)
    clearance = db.Column(db.Boolean, unique=False, nullable=False)
    orders = relationship("Order", back_populates="customer")


# Item Config
class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    category = db.Column(db.String, unique=False, nullable=False)
    price = db.Column(db.Float, unique=False, nullable=False)
    unit = db.Column(db.String, unique=False, nullable=False)
    unit_amt = db.Column(db.Float, unique=False, nullable=False)
    img_url = db.Column(db.String, unique=False, nullable=False)
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


# --- Initialize db for first time --- #
# with app.app_context():
#     db.create_all()


@app.route("/")
def home():
    db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
    items = [item for item in db_items]
    return render_template("index.html", logged_in=current_user.is_authenticated, items=items)


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not user:
            flash("That email does not have an account. Please try again.")
            return redirect(url_for("login", form=form))
        elif not check_password_hash(user.password, password):
            flash("Incorrect password. Please try again.")
            return redirect(url_for("login", form=form))
        else:
            login_user(user)
            return redirect(url_for("home"))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout', methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/sign-up', methods=["GET", "POST"])
def sign_up():
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        hash_password = generate_password_hash(form.password.data, salt_length=8)
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not user:
            if email == os.getenv('ADMIN_EMAIL'):
                clearance = True
            else:
                clearance = False

            new_user = User(
                email = email,
                username = form.username.data,
                password = hash_password,
                clearance = clearance
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("home"))
        else:
            flash("That email is already registered. Please log in.")
            return redirect(url_for("login", logged_in=current_user.is_authenticated))
    return render_template("sign_up.html", form=form)


@app.route("/add-item", methods=['GET', 'POST'])
@admin_only
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        new_item = Item(
            name = form.name.data,
            category = form.category.data,
            price = form.price.data,
            unit = form.unit.data,
            unit_amt = form.unit_amt.data,
            img_url = form.img_url.data,
            stock = form.stock.data,
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for("home", logged_in=current_user.is_authenticated))
    return render_template("add_item.html", current_user=current_user, form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-item/<int:item_id>")
@admin_only
def edit_item(item_id):
    form = ItemForm()
    item = db.get_or_404(Item, item_id)
    if form.validate_on_submit():
        item.name = form.name.data
        item.price = form.price.data
        item.unit = form.unit.data
        item.unit_amt = form.unit_amt.data
        item.img_url = form.img_url.data
        item.stock = form.stock.data
    
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit_item.html", current_user=current_user, form=form, current_item=item)


# @app.route("/syrups")
# def syrup():
#     # db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
#     # items = [item for item in db_items]
#     return render_template("syrups.html")
# # Add salesfront=items as a **kwarg


if __name__ == '__main__':
    app.run(debug=True)
