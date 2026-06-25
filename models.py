from flask_login import UserMixin
from extensions import db

# ---------------- USER MODEL ----------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)  # Unique username
    password = db.Column(db.String(200), nullable=False)  # Hashed password
    role = db.Column(db.String(10), nullable=False)  # 'admin' or 'user'
    # Relationship: User can have multiple requests
    requests = db.relationship('Request', backref='user', lazy=True)

# ---------------- ASSET MODEL ----------------
class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Asset name
    serial_number = db.Column(db.String(100), unique=True, nullable=False)  # Unique serial
    type = db.Column(db.String(50), nullable=False)  # e.g., Laptop, Phone
    status = db.Column(db.String(20), default='available')  # Status: available, assigned, maintenance
    # Relationship: Asset can have many requests
    requests = db.relationship(
        'Request',
        backref='asset',
        lazy=True,
        cascade="all, delete-orphan"  # Ensures requests linked to an asset are deleted when asset is deleted
    )

# ---------------- REQUEST MODEL ----------------
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to user
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)  # Link to asset
    status = db.Column(db.String(20), default='pending')  # Status: pending, approved, denied, revoked
    reason = db.Column(db.Text)  # User's reason for request
