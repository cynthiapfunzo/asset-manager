import os
from datetime import datetime, timedelta, date
import dotenv
from flask_ldap3_login import LDAP3LoginManager
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, flash, render_template, redirect, url_for, request, session, current_app, jsonify
from werkzeug.utils import secure_filename

from models import db, Asset, User


app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["SQLALCHEMY_DATABASE_URI"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration for LDAP
app.config['LDAP_HOST'] = 'ldap://your-ldap-server'
app.config['LDAP_BASE_DN'] = 'DC=example,DC=com'
app.config['LDAP_USER_DN'] = 'OU=Users'
app.config['LDAP_GROUP_DN'] = 'OU=Groups'
app.config['LDAP_BIND_USER_DN'] = 'CN=bind_user,OU=Users,DC=example,DC=com'
app.config['LDAP_BIND_USER_PASSWORD'] = 'bind_password'
app.config['LDAP_USER_RDN_ATTR'] = 'cn'
app.config['LDAP_USER_LOGIN_ATTR'] = 'sAMAccountName'
app.config['LDAP_BIND_AUTH'] = True

app.secret_key = os.urandom(24)

db.init_app(app)

ldap_manager = LDAP3LoginManager(app)
login_manager = LoginManager()
login_manager.init_app(app)

# User class for Flask-Login
class UserM(UserMixin):
    def __init__(self, username, dn, data):
        self.id = username
        self.dn = dn
        self.data = data

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# Route for borrowing an item
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    if search_query:
        assets = Asset.query.filter(Asset.asset_number.like(f'%{search_query}%')).all()
    else:
        assets = Asset.query.all()
    return render_template('inventory.html', assets=assets)

@app.route('/borrowed')
@login_required
def borrowed():
    search_query = request.args.get('search', '')
    if search_query:
        borrowed_assets = Asset.query.filter(Asset.is_borrowed == True, Asset.asset_number.like(f'%{search_query}%')).all()
    else:
        borrowed_assets = Asset.query.filter_by(is_borrowed=True).all()
    for asset in borrowed_assets:
        if asset.borrow_date and asset.borrow_length:
            asset.return_date = asset.borrow_date + timedelta(days=asset.borrow_length)
        else:
            asset.return_date = None
    current_date = date.today()
    return render_template('borrowed.html', assets=borrowed_assets, current_date=current_date)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form['name']
        asset_type = request.form['type']
        serial_number = request.form['serial_number']
        asset_number = request.form['asset_number']

        # Handle file upload
        photo = request.files['photo']
        photo_uri = None
        if photo:
            # Secure the filename and save it
            filename = secure_filename(photo.filename)
            upload_folder = os.path.join(current_app.static_folder, 'uploads')

            # Create the uploads folder if it doesn't exist
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # Construct the path to save the file
            photo_path = os.path.join(upload_folder, filename)
            photo_uri = os.path.join('static/uploads', filename)

            # Save the file to the specified folder
            photo.save(photo_path)

        new_asset = Asset(
            name=name,
            type=asset_type,
            serial_number=serial_number,
            asset_number=asset_number,
            photo_path=photo_uri
        )
        db.session.add(new_asset)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')


@app.route('/borrow/<int:asset_id>', methods=['POST'])
def borrow_asset(asset_id):
    data = request.get_json()
    borrower_name = data['borrower_name']
    borrow_date = data['borrow_date']
    borrow_length = data['borrow_length']

    asset = Asset.query.get(asset_id)
    if asset and not asset.is_borrowed:
        asset.is_borrowed = True
        asset.borrower_name = borrower_name
        asset.borrow_date = datetime.strptime(borrow_date, '%Y-%m-%d')  # Parse the date
        asset.borrow_length = borrow_length
        db.session.commit()
        return jsonify(success=True), 200
    return jsonify(success=False, error="Asset not available"), 400


@app.route('/return/<int:asset_id>', methods=['POST'])
def return_asset(asset_id):
    asset = Asset.query.get(asset_id)
    if asset and asset.is_borrowed:
        asset.is_borrowed = False
        asset.borrower_name = None  # Clear the borrower's name
        asset.borrow_date = None     # Clear the borrow date
        asset.borrow_length = None    # Clear the borrow length
        db.session.commit()
        return '', 204  # No content
    return '', 404  # Not found


@app.route('/statistics')
@login_required
def statistics():
    assets = Asset.query.all()

    types = {}
    for asset in assets:
        if asset.type not in types:
            types[asset.type] = {'borrowed': 0, 'remaining': 0}
        if asset.is_borrowed:
            types[asset.type]['borrowed'] += 1
        else:
            types[asset.type]['remaining'] += 1

    return render_template('statistics.html', types=types)


@app.route('/delete_asset/<int:asset_id>', methods=['POST'])
@login_required  # Optional: if you want only logged-in users to delete
def delete_asset(asset_id):
    # Query the asset by ID
    asset = Asset.query.get_or_404(asset_id)

    try:
        db.session.delete(asset)
        db.session.commit()
        flash(f'Asset {asset.name} has been successfully deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting asset: {str(e)}', 'danger')

    return redirect(url_for('index'))  # Redirect to the inventory page

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = ""
    password = ""
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin":
            user = User.query.filter_by(username=username).first()
            login_user(user)
            return redirect("/")
        else:
            error = "Username or password wrong."
    return render_template('login.html', username=username, password=password, error=error)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

