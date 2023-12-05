from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import DecimalField, IntegerField, StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


# Item Form
class ItemForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired()])
    price = DecimalField("Price (USD)", places=2, validators=[DataRequired()])
    unit = StringField("Weight/Volume Unit (oz, g, or ml)", validators=[DataRequired()])
    unit_amt = DecimalField("Weight/Volume Amount", places=1, validators=[DataRequired()])
    img_url = StringField("Product Image URL", validators=[DataRequired(), URL()])
    stock = IntegerField("Stock", validators=[DataRequired()])
    submit = SubmitField("Create New Item")


# Signup Form
class SignupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Create Account")


# Login Form
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")
