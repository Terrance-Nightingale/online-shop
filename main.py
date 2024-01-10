import os
from datetime import date
from xml.dom.minidom import Attr
from sqlalchemy import Null, Nullable
import stripe
from forms import *
from dotenv import load_dotenv
from flask import Flask, abort, flash, render_template, redirect, url_for, request, jsonify
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


# Set up Stripe Checkout session
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
YOUR_DOMAIN = os.getenv('DOMAIN')


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
    stripe_prod_id = db.Column(db.String, unique=True, nullable=False)
    stripe_price_id = db.Column(db.String, unique=True, nullable=False)
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
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"))
    item = relationship('Item', foreign_keys='OrderItem.item_id')
    parent_order = relationship("Order", back_populates="items")
    parent_cart = relationship("Cart", back_populates="items")
    quantity = db.Column(db.Integer, unique=False, nullable=False)


# Order Config
# !! Shipping and billing addresses will be dealt with on the Stripe dashboard !!

class Order(UserMixin, db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    date = db.Column(db.String(250))
    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="parent_order")
    # shipping_address = db.Column(db.String, nullable=True)
    # billing_address = db.Column(db.String, nullable=True)
    
# Cart Config
class Cart(UserMixin, db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
    return render_template("profile.html", user=user, logged_in=current_user.is_authenticated)


@app.route('/edit-profile/<string:user_name>/<int:user_id>', methods=["GET", "POST"])
def edit_profile(user_name, user_id):
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


@app.route('/string:user_name>/my_orders', methods=["GET"])
def my_orders():
        return render_template("my_orders.html", logged_in=current_user.is_authenticated)


@app.route('/string:user_name>/my_orders/<int:order_id>', methods=["GET"])
def order(order_id):
        order = db.get_or_404(Order, order_id)
        return render_template("order.html", logged_in=current_user.is_authenticated, order=order)



#--- Item-Relevant Pages ---#
@app.route('/item/<int:item_id>')
def goto_item(item_id):
    # Grab current item
    item = db.get_or_404(Item, item_id) 

    # Grab current cart if it exists
    try:
        if current_user.cart:
            cart = current_user.cart
            # If cart exists, retrieve OrderItem (if any) that corresponds to the current Item
            order_item = db.session.execute(db.select(OrderItem).where(OrderItem.item_id == item_id, OrderItem.cart_id == cart.id)).scalar()
        else:
            order_item = Null
    
    # Redirect anonymous user to login page
    except AttributeError:
        return redirect(url_for('login'))

    return render_template("item.html", logged_in=current_user.is_authenticated, item=item, order_item=order_item)


@app.route("/add-item", methods=['GET', 'POST'])
@admin_only
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        # Create new Product in Stripe db
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

        # Create Price for new item in Stripe db
        new_price = stripe.Price.create(
            product=new_product.id,
            currency="usd",
            unit_amount=form.price.data,
            nickname=form.name.data,
        )

        # Create Item in local db
        new_item = Item(
            stripe_prod_id = new_product.id,
            stripe_price_id = new_price.id,
            name = form.name.data,
            category = form.category.data,
            price = form.price.data,
            unit = form.unit.data,
            unit_amt = form.unit_amt.data,
            img_url = form.img_url.data,
            description = form.description.data,
            stock = form.stock.data,
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
        # Modify associated product in Stripe db
        stripe.Product.modify(item.stripe_prod_id,
                              name=form.name.data,
                              description=form.description.data,
                              metadata={
                                  'category': form.category.data,
                                  'unit': form.unit.data,
                                  'unit_amt': form.unit_amt.data,
                                  'stock': form.stock.data
                                  },
                              images=[form.img_url.data])
        
        if form.price.data != item.price:
            # Inactivate old Price
            stripe.Price.modify(item.stripe_price_id, active=False)

            # Create new Price for Product in Stripe db
            new_price = stripe.Price.create(
                product=item.stripe_prod_id,
                currency="usd",
                unit_amount=form.price.data,
                nickname=form.name.data,
            )

            # Modify produce price in local db
            item.stripe_price_id = new_price.id

        # Modify product in local db
        item.name = form.name.data
        item.category = form.category.data
        item.price = form.price.data
        item.unit = form.unit.data
        item.unit_amt = form.unit_amt.data
        item.img_url = form.img_url.data
        item.description = form.description.data
        item.stock = form.stock.data

        db.session.commit()
        return redirect(url_for("home", logged_in=current_user.is_authenticated, item_id=item.id))
    return render_template("edit_item.html", logged_in=current_user.is_authenticated, current_user=current_user, editing=True, form=form, item=item)


@app.route("/confirm-delete/<int:item_id>", methods=['GET', 'POST', 'DELETE'])
@admin_only
def confirm_delete_item(item_id):
    item_to_delete = db.get_or_404(Item, item_id)
    form = ConfirmDeleteForm()

    if form.validate_on_submit():
        # Inactivate Product in Stripe db
        stripe.Product.modify(item_to_delete.stripe_prod_id, active=False)

        # Delete product in local db
        db.session.delete(item_to_delete)
        db.session.commit()
        return redirect(url_for("home", logged_in=current_user.is_authenticated))
    return render_template("delete_item.html", logged_in=current_user.is_authenticated, form=form)



#--- Cart-Relevant Pages ---#
@app.route('/add-to-cart/<int:item_id>/<increment>')
def cart_add(item_id, increment):
    try:
        if not current_user.cart:
            cart = Cart(
                user_id=current_user.id, 
                customer=current_user
                )
                
            db.session.add(cart)
            db.session.commit()
        else:
            cart = current_user.cart
    
    # Redirect anonymous user to login page
    except AttributeError:
        return redirect(url_for('login'))


    filter_item = db.session.query(OrderItem).filter(OrderItem.item_id == item_id, OrderItem.cart_id == cart.id)
    search_item = db.session.execute(db.select(OrderItem).where(OrderItem.item_id == item_id, OrderItem.cart_id == cart.id)).scalar()

    # If the cart has no items or if the current item being added is not yet in the cart, creates a new OrderItem and adds it to the cart
    if not cart.items or not filter_item or not search_item:
        order_item = OrderItem(
        item_id=item_id,
        quantity=0,
        parent_cart=cart
        )
        print(order_item.quantity)

        db.session.add(order_item)
    else:
        order_item = search_item
        print(order_item.quantity)

    # Add or remove 1 qty of the current item from the cart
    if increment == 'plus':
        order_item.quantity += 1
    elif increment == 'minus' and order_item.quantity > 0:
        order_item.quantity -= 1

    db.session.commit()
    return redirect(url_for("goto_item", item_id=item_id, logged_in=current_user.is_authenticated))


@app.route('/create-checkout-session', methods=['GET', 'POST'])
def create_checkout_session():
    # Attempts to pull current user's cart (if any). Redirects user to empty cart page if no cart found
    cart = current_user.cart
    cart_qty = 0

    print(cart)

    if cart == None:
        return redirect(url_for("empty", logged_in=current_user.is_authenticated))
    else:
        for item in cart.items:
            cart_qty += item.quantity
        if cart_qty == 0:
            return redirect(url_for("empty", logged_in=current_user.is_authenticated))
    
        # Attempts to create a checkout.Session and populates line_items with contents of cart. Returns error if unsuccessful
        try:
            checkout_session = stripe.checkout.Session.create(
                shipping_address_collection={"allowed_countries": ["US", "CA"]},
                shipping_options=[
                {
                    "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": 0, "currency": "usd"},
                    "display_name": "Free shipping",
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 5},
                        "maximum": {"unit": "business_day", "value": 7},
                    },
                    },
                },
                {
                    "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": 500, "currency": "usd"},
                    "display_name": "Two-day shipping",
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 2},
                        "maximum": {"unit": "business_day", "value": 2},
                    },
                    },
                },
                {
                    "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": 1500, "currency": "usd"},
                    "display_name": "Next day air",
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 1},
                        "maximum": {"unit": "business_day", "value": 1},
                    },
                    },
                },
                ],
                line_items=[{'price': f'{order_item.item.stripe_price_id}', 'quantity': order_item.quantity} for order_item in cart.items if order_item.quantity > 0],
                mode='payment',
                success_url= YOUR_DOMAIN + 'success',
                cancel_url= YOUR_DOMAIN + 'cancel',
            )
        except Exception as e:
            return str(e)

    return redirect(checkout_session.url, code=303)


@app.route('/success', methods=['GET', 'POST'])
def success():
    # Create Order and links cart items to it
    cart = current_user.cart
    order = Order(
        user_id = current_user.id,
        date = date.today().strftime("%m/%d/%Y")
    )
    db.session.add(order)

    for item in cart.items:
        if item.quantity > 0:
            item.order_id = order.id
        item.cart_id = Null

    # Delete the Cart
    db.session.delete(current_user.cart)
    db.session.commit()
    return render_template('success.html', logged_in=current_user.is_authenticated)


@app.route('/cancel', methods=['GET'])
def cancel():
    return render_template('cancel.html', logged_in=current_user.is_authenticated)


@app.route('/cart-empty', methods=['GET'])
def empty():
    return render_template('empty.html', logged_in=current_user.is_authenticated)


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


# TODO 7) Add Inventory page for admin
# TODO 8) Add Customer list page for admin
