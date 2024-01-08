import os
from sqlalchemy import Nullable
import stripe
import json
from forms import *
from turtle import back
from dotenv import load_dotenv
from flask import Flask, abort, flash, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

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


# Set up Stripe Checkout session
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
YOUR_DOMAIN = 'http://localhost:4242'


# User Config
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(50), unique=False, nullable=False)
    clearance = db.Column(db.Boolean, unique=False, nullable=False)
    shipping_address = db.Column(db.String, nullable=True)
    billing_address = db.Column(db.String, nullable=True)
    orders = relationship("Order", back_populates="customer")
    cart = relationship("Cart", back_populates="customer", uselist=False)


# Item Config
class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    category = db.Column(db.String, unique=False, nullable=False)
    price = db.Column(db.Float, unique=False, nullable=False)
    unit = db.Column(db.String, unique=False, nullable=False)
    unit_amt = db.Column(db.Float, unique=False, nullable=False)
    description = db.Column(db.String, nullable=False)
    img_url = db.Column(db.String, unique=False, nullable=False)
    stock = db.Column(db.Integer, unique=False, nullable=False)


# Ordered Item Config
class OrderItem(UserMixin, db.Model):
    __tablename__ = "ordered-items"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"))
    parent_order = relationship("Order", back_populates="items")
    parent_cart = relationship("Cart", back_populates="items")
    quantity = db.Column(db.Integer, unique=False, nullable=False)


# Order Config
class Order(UserMixin, db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="parent_order")
    shipping_address = db.Column(db.String, nullable=True)
    billing_address = db.Column(db.String, nullable=True)
    
# Cart Config
class Cart(UserMixin, db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    customer = relationship("User", back_populates="cart")
    items = relationship("OrderItem", back_populates="parent_cart")


# --- Initialize db for first time --- #
with app.app_context():
    db.create_all()


#--- Home Page ---#
@app.route("/")
def home():
    db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
    items = [item for item in db_items]
    return render_template("index.html", logged_in=current_user.is_authenticated, items=items)


#--- Account-Relevant Pages ---#
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


@app.route('/<string:user_name>/<int:user_id>/my-profile', methods=["GET", "POST"])
def profile(user_name, user_id):
    user = db.get_or_404(User, user_id)
    return render_template("profile.html", user=user)


@app.route('/edit-profile/<string:user_name>/<int:user_id>', methods=["GET", "POST"])
def edit_profile(user_id):
    user = db.get_or_404(User, user_id)
        
    form = EditProfileForm(
        username = user.username,
        email = user.email,
    )

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data

        db.session.commit()
        return redirect(url_for("home", logged_in=current_user.is_authenticated))
    return render_template("edit_profile.html", logged_in=current_user.is_authenticated, form=form)


@app.route('/change-password/<string:user_name>/<int:user_id>', methods=["GET", "POST"])
def change_password(user_name, user_id):
    user = db.get_or_404(User, user_id) 
    form = ChangePassForm()

    if request.method == "POST":
        if form.validate_on_submit() and form.password.data == form.verify_pass.data:
            hash_password = generate_password_hash(form.verify_pass.data, salt_length=8)
            user.password = hash_password

            db.session.commit()
            return redirect(url_for("home", logged_in=current_user.is_authenticated))
        else:
            flash("Password must match in both input fields.")
            return redirect(url_for("change_password", name=user_name, user_id=user_id, logged_in=current_user.is_authenticated, form=form))
    return render_template("change_password.html", logged_in=current_user.is_authenticated, form=form)


#--- Item-Relevant Pages ---#
@app.route('/item/<int:item_id>')
def goto_item(item_id):
    item = db.get_or_404(Item, item_id) 
    return render_template("item.html", logged_in=current_user.is_authenticated, item=item)


@app.route("/add-item", methods=['GET', 'POST'])
@admin_only
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        # Create Item in local database
        new_item = Item(
            name = form.name.data,
            category = form.category.data,
            price = form.price.data,
            unit = form.unit.data,
            unit_amt = form.unit_amt.data,
            img_url = form.img_url.data,
            description = form.description.data,
            stock = form.stock.data,
        )

        # Create new Product in Stripe database
        new_product = stripe.Product.create(
            name=form.name.data,
            description=form.description.data,
            metadata={
                'category': form.category.data,
                'unit': form.unit.data,
                'unit_amt': form.unit_amt.data,
                'stock': form.stock.data
                },
            images=[form.img_url.data]
            )

        # Create Price for new item in Stripe database
        stripe.Price.create(
            product=new_product.id,
            currency="usd",
            unit_amount=form.price.data,
            nickname=form.name.data,
        )

        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for("home", logged_in=current_user.is_authenticated))
    return render_template("add_item.html", current_user=current_user, form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-item/<int:item_id>", methods=["GET", "POST", "UPDATE"])
@admin_only
def edit_item(item_id):
    item = db.get_or_404(Item, item_id)
    form = ItemForm(
        name = item.name,
        category = item.category,
        price = item.price,
        unit = item.unit,
        unit_amt = item.unit_amt,
        img_url = item.img_url,
        description = item.description,
        stock = item.stock
    )

    if form.validate_on_submit():
        item.name = form.name.data
        item.category = form.category.data
        item.price = form.price.data
        item.unit = form.unit.data
        item.unit_amt = form.unit_amt.data
        item.img_url = form.img_url.data
        item.description = form.description.data
        item.stock = form.stock.data

        
        stripe.Product.modify(
        "prod_NWjs8kKbJWmuuc",
        metadata={"order_id": "6735"},
        )
    
        db.session.commit()
        return redirect(url_for("goto_item", logged_in=current_user.is_authenticated, item_id=item.id))
    return render_template("edit_item.html", logged_in=current_user.is_authenticated, current_user=current_user, editing=True, form=form, item=item)


@app.route("/confirm-delete/<int:item_id>", methods=['GET', 'POST', 'DELETE'])
@admin_only
def confirm_delete_item(item_id):
    item_to_delete = db.get_or_404(Item, item_id)
    form = ConfirmDeleteForm()

    if form.validate_on_submit():
        db.session.delete(item_to_delete)
        db.session.commit()
        return redirect(url_for("home", logged_in=current_user.is_authenticated))
    return render_template("delete_item.html", logged_in=current_user.is_authenticated, form=form)



#--- Cart-Relevant Pages ---#
@app.route('/add-to-cart/<int:item_id>')
def cart_add(item_id):
    try:
        # Try to find the current user's cart
        cart = current_user.cart

        # If the user doesn't have a cart, create a new one
        if cart is None:
            cart = Cart(user_id=current_user.id, customer=current_user)
            db.session.add(cart)
            db.session.commit()

        # Try to find an existing order item for the given item_id and cart
        order_item = db.session.query(OrderItem).filter(
            OrderItem.item_id == item_id,
            OrderItem.cart_id == cart.id
        ).one()

    except NoResultFound:
        # If not found, create a new order item
        order_item = OrderItem(
            item_id=item_id,
            quantity=0,
            parent_cart=cart
        )
        db.session.add(order_item)

    # Increment the quantity
    order_item.quantity += 1

    # Commit changes
    db.session.commit()

    return redirect(url_for("home", logged_in=current_user.is_authenticated))


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': '{{PRICE_ID}}',
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '/success.html',
            cancel_url=YOUR_DOMAIN + '/cancel.html',
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


#--- Product Category Pages ---#
@app.route("/syrups")
def syrup():
    db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
    items = [item for item in db_items if item.category == "syrup"]
    return render_template("index.html", logged_in=current_user.is_authenticated, items=items)


@app.route("/hot-sauces")
def hot_sauce():
    db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
    items = [item for item in db_items if item.category == "hotsauce"]
    return render_template("index.html", logged_in=current_user.is_authenticated, items=items)


@app.route("/jams")
def jam():
    db_items = db.session.execute(db.select(Item).order_by('id')).scalars()
    items = [item for item in db_items if item.category == "jam"]
    return render_template("index.html", logged_in=current_user.is_authenticated, items=items)


if __name__ == '__main__':
    app.run(debug=True)


# TODO 5) Add page to view My Orders (current and past)
# TODO 6) Add Checkout page to view cart. If nothing is in the cart, pull up the page showing that cart is empty.
# TODO 7) Add Inventory page for admin
# TODO 8) Add Customer list page for admin
# TODO 9) Add "+" and "-" so that cart can be adjusted
