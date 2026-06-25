from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp


ASSET_STATUS_CHOICES = [
    ('available', 'Available'),
    ('assigned', 'Assigned'),
    ('maintenance', 'Maintenance'),
]

SAFE_TEXT_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 .,'()/&+-]*$"


def strip_whitespace(value):
    return value.strip() if isinstance(value, str) else value

# ---------------- REGISTER FORM ----------------
class RegisterForm(FlaskForm):
    username = StringField(
        'Username',
        filters=[strip_whitespace],
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
            Length(min=10, max=128, message="Password must be between 10 and 128 characters."),
            Regexp(r'.*[a-z].*', message="Password must include a lowercase letter."),
            Regexp(r'.*[A-Z].*', message="Password must include an uppercase letter."),
            Regexp(r'.*\d.*', message="Password must include a number."),
            Regexp(r'.*[^A-Za-z0-9].*', message="Password must include a symbol."),
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('password', message="Passwords must match."),
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
    asset_id = SelectField('Asset', coerce=int, validators=[DataRequired()])  # Dropdown to select asset (integer IDs)
    reason = TextAreaField(
        'Reason for request',
        filters=[strip_whitespace],
        validators=[
            DataRequired(),
            Length(min=10, max=500, message="Reason must be between 10 and 500 characters."),
        ]
    )
    submit = SubmitField('Submit Request')

# ---------------- ASSET FORMS ----------------
class AssetForm(FlaskForm):
    name = StringField(
        'Name',
        filters=[strip_whitespace],
        validators=[
            DataRequired(),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
            Regexp(SAFE_TEXT_PATTERN, message="Name contains unsupported characters."),
        ]
    )
    serial = StringField(
        'Serial Number',
        filters=[strip_whitespace],
        validators=[
            DataRequired(),
            Length(min=3, max=100, message="Serial number must be between 3 and 100 characters."),
            Regexp(r'^[A-Za-z0-9][A-Za-z0-9._-]*$', message="Serial number may only contain letters, numbers, dots, underscores, and hyphens."),
        ]
    )
    type = StringField(
        'Type',
        filters=[strip_whitespace],
        validators=[
            DataRequired(),
            Length(min=2, max=50, message="Type must be between 2 and 50 characters."),
            Regexp(SAFE_TEXT_PATTERN, message="Type contains unsupported characters."),
        ]
    )
    submit = SubmitField('Add Asset')


class EditAssetForm(AssetForm):
    status = SelectField(
        'Status',
        choices=ASSET_STATUS_CHOICES,
        validators=[DataRequired()]
    )
    submit = SubmitField('Update Asset')
