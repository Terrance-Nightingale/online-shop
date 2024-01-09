from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import DecimalField, FileField, IntegerField, SelectField, StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


# Item Form
class ItemForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired()])
    category = SelectField("Product Type", choices=[("syrup", "Syrup"), ("hotsauce", "Hot Sauce"), ("jam", "Jam/Jelly")], coerce=str,  validators=[DataRequired()])
    price = IntegerField("USD Price (in cents)", validators=[DataRequired()])
    unit = SelectField("Weight/Volume Unit (oz, g, or ml)", choices=[("oz", "Ounces"), ("g", "Grams"), ("ml", "Milliliters")], validators=[DataRequired()])
    unit_amt = DecimalField("Weight/Volume Amount", places=1, validators=[DataRequired()])
    img_url = StringField("Product Image URL", validators=[DataRequired(), URL()])
    stock = IntegerField("Stock", validators=[DataRequired()])
    description = StringField("Item Description", validators=[DataRequired()])
    submit = SubmitField("Save Changes")


#Confirm Item Delete Form
class ConfirmDeleteForm(FlaskForm):
    confirmation = SubmitField("Remove item permanently")


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


# Profile Edit Form
class EditProfileForm(FlaskForm):
    username = StringField("Username")
    email = StringField("Email")
    submit = SubmitField("Save Edits")


# Change Password Form
class ChangePassForm(FlaskForm):
    password = StringField("New Password", validators=[DataRequired()])
    verify_pass = PasswordField("Verify Password", validators=[DataRequired()])
    submit = SubmitField("Save Edits")
