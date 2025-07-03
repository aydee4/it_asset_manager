from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Regexp

# ---------------- REGISTER FORM ----------------
class RegisterForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=20, message="Username must be between 3 and 20 characters."),  # Enforce username length
            Regexp(r'^[A-Za-z0-9]+$', message="Username must contain only letters and numbers.")  # Alphanumeric only
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=8, max=20, message="Password must be between 8 and 20 characters."),
            Regexp(r'^[A-Za-z0-9]+$', message="Password must contain only letters and numbers.")  # Alphanumeric only
        ]
    )
    submit = SubmitField('Register')

# ---------------- LOGIN FORM ----------------
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])  # Username required
    password = PasswordField('Password', validators=[DataRequired()])  # Password required
    submit = SubmitField('Login')

# ---------------- ASSET REQUEST FORM ----------------
class RequestForm(FlaskForm):
    asset_id = SelectField('Asset', coerce=int)  # Dropdown to select asset (integer IDs)
    reason = TextAreaField('Reason for request', validators=[DataRequired()])  # Required reason
    submit = SubmitField('Submit Request')
