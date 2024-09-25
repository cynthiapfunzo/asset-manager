import os
from app import app, db

with app.app_context():
    db_file = 'assets.db'  # Your database file name
    if os.path.exists(db_file):
        os.remove(db_file)  # Remove the existing database file
    db.create_all()  # Create a new database and tables
