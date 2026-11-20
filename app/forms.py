from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError
from app.models import User

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")

class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters."),
    ])
    confirm = PasswordField("Confirm Password", validators=[
        DataRequired(),
        EqualTo("password", message="Passwords do not match."),
    ])
    agree = BooleanField("I agree", validators=[
        DataRequired(message="You must agree to continue."),
    ])
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("An account with this email already exists.")

class VerifyForm(FlaskForm):
    code = StringField("Verification code", validators=[
        DataRequired(message="Enter the 6-digit code."),
        Regexp(r"^\d{6}$", message="The code is 6 digits."),
    ])
    submit = SubmitField("Verify")

class ForgotForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send code")

class ResetForm(FlaskForm):
    code = StringField("Reset code", validators=[
        DataRequired(message="Enter the 6-digit code."),
        Regexp(r"^\d{6}$", message="The code is 6 digits."),
    ])
    password = PasswordField("New password", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters."),
    ])
    confirm = PasswordField("Confirm new password", validators=[
        DataRequired(),
        EqualTo("password", message="Passwords do not match."),
    ])
    submit = SubmitField("Reset password")

from wtforms import SelectField, RadioField, TextAreaField
from wtforms.validators import Optional

COUNTRIES = [
    ("Philippines", "Philippines"),
    ("United States", "United States"),
    ("Canada", "Canada"),
    ("Australia", "Australia"),
    ("Singapore", "Singapore"),
    ("Japan", "Japan"),
]

class DeliveryForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Phone Number", validators=[
        DataRequired(),
        Regexp(r"^\+?[0-9\s()\-]{7,20}$", message="Enter a valid phone number."),
    ])
    country = SelectField("Country / Region", choices=COUNTRIES, validators=[DataRequired()])
    street_address = StringField("Street Address", validators=[DataRequired(), Length(max=255)])
    apartment = StringField("Apartment, Suite, etc. (Optional)", validators=[Optional(), Length(max=120)])
    city = StringField("City", validators=[DataRequired(), Length(max=80)])
    province = StringField("State / Province", validators=[DataRequired(), Length(max=80)])
    postal_code = StringField("Postal Code", validators=[DataRequired(), Length(max=20)])
    delivery_instructions = TextAreaField("Delivery Instructions (Optional)", validators=[Optional(), Length(max=500)])
    delivery_preference = RadioField("Delivery Preferences", choices=[
        ("standard", "Standard Shipping (3-5 Business Days)"),
        ("express", "Express Shipping (1-2 Business Days)"),
    ], default="standard", validators=[DataRequired()])
    submit = SubmitField("Save & Continue")

class ChangePasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired()])
    new = PasswordField("New password", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters."),
    ])
    confirm = PasswordField("Confirm new password", validators=[
        DataRequired(),
        EqualTo("new", message="Passwords do not match."),
    ])
    submit = SubmitField("Update password")
