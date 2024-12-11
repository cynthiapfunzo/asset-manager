from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = "pfunzo_user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Asset(db.Model):
    __tablename__ = "pfunzo_asset"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    serial_number = db.Column(db.String(100), nullable=False)
    asset_number = db.Column(db.String(100), nullable=True)  # Ensure this field exists
    photo_path = db.Column(db.String(200), nullable=True)
    is_borrowed = db.Column(db.Boolean, default=False)
    borrower_name = db.Column(db.String(100), nullable=True)
    borrow_date = db.Column(db.DateTime, nullable=True)
    borrow_length = db.Column(db.Integer, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
