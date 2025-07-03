from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy import case

from extensions import db, login_manager
from forms import RegisterForm, LoginForm, RequestForm
from models import User, Asset, Request as AssetRequest

# ---------------- APP SETUP ----------------

# Initialise Flask app and configure secret key & database
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'  # Secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assets.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialise Flask extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect unauthenticated users here

# Load user for Flask-Login using user_id stored in session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    # If user is logged in, go straight to dashboard; else show landing page
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        # Hash password before saving to database
        hashed_pw = generate_password_hash(form.password.data)
        user = User(username=form.username.data, password=hashed_pw, role='user')
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    elif form.errors:
        flash('Please correct the errors in the form.', 'danger')
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # Verify password using hash
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash(f'Welcome, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Order assets: available first, then maintenance, then assigned
    assets = Asset.query.order_by(
        case(
            (Asset.status == 'available', 0),
            (Asset.status == 'maintenance', 1),
            (Asset.status == 'assigned', 2)
        )
    ).all()
    # Show pending request count for admin dashboard badge
    pending_count = AssetRequest.query.filter_by(status='pending').count() if current_user.role == 'admin' else 0
    return render_template('dashboard.html', assets=assets, pending_count=pending_count)

@app.route('/request_asset', methods=['GET', 'POST'])
@login_required
def request_asset():
    form = RequestForm()
    # Populate dropdown with available assets
    form.asset_id.choices = [(a.id, a.name) for a in Asset.query.filter_by(status='available')]

    if form.validate_on_submit():
        asset = Asset.query.get(form.asset_id.data)
        # Double-check asset availability (in case status changed during form fill)
        if not asset or asset.status != 'available':
            flash('This asset is no longer available.', 'danger')
            return redirect(url_for('dashboard'))

        new_request = AssetRequest(
            user_id=current_user.id,
            asset_id=form.asset_id.data,
            reason=form.reason.data,
            status='pending'
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Asset request submitted.', 'success')
        return redirect(url_for('dashboard'))
    elif form.errors:
        flash('Please correct the errors in your request.', 'danger')

    # Get unavailable (assigned) assets for information display
    unavailable_assets = []
    assigned_assets = Asset.query.filter_by(status='assigned').all()
    for asset in assigned_assets:
        active_request = next(
            (req for req in asset.requests if req.status == 'approved'),
            None
        )
        assigned_user = active_request.user.username if active_request else "Unknown"
        unavailable_assets.append((asset, assigned_user))

    return render_template('request_asset.html', form=form, unavailable_assets=unavailable_assets)

@app.route('/admin')
@login_required
def admin():
    # Ensure only admins can view
    if current_user.role != 'admin':
        flash('Access denied: admin only.', 'danger')
        return redirect(url_for('dashboard'))
    # List all pending asset requests
    requests = AssetRequest.query.filter_by(status='pending').all()
    return render_template('admin_panel.html', requests=requests)

@app.route('/admin/approve/<int:request_id>')
@login_required
def approve_request(request_id):
    # Only admin can approve
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    asset_request = AssetRequest.query.get_or_404(request_id)
    asset = Asset.query.get(asset_request.asset_id)

    asset_request.status = 'approved'
    asset.status = 'assigned'

    db.session.commit()
    flash('Request approved and asset assigned.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/deny/<int:request_id>')
@login_required
def deny_request(request_id):
    # Only admin can deny
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    asset_request = AssetRequest.query.get_or_404(request_id)
    asset_request.status = 'denied'

    db.session.commit()
    flash('Request denied.', 'info')
    return redirect(url_for('admin'))

# Decorator to require admin role for route access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/assets')
@login_required
@admin_required
def asset_list():
    assets = Asset.query.all()
    return render_template('assets.html', assets=assets)

@app.route('/assets/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_asset():
    if request.method == 'POST':
        name = request.form['name']
        serial = request.form['serial']
        type_ = request.form['type']

        # Prevent duplicate serial numbers
        existing_asset = Asset.query.filter_by(serial_number=serial).first()
        if existing_asset:
            flash('Asset with that serial number already exists.', 'danger')
            return redirect(url_for('add_asset'))

        asset = Asset(name=name, serial_number=serial, type=type_)
        db.session.add(asset)
        db.session.commit()
        flash('Asset added.', 'success')
        return redirect(url_for('asset_list'))
    return render_template('add_asset.html')

@app.route('/assets/edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if request.method == 'POST':
        new_serial = request.form['serial']
        # Prevent serial number collision with other assets
        existing_asset = Asset.query.filter(Asset.serial_number==new_serial, Asset.id!=asset.id).first()
        if existing_asset:
            flash('Another asset with that serial number already exists.', 'danger')
            return redirect(url_for('edit_asset', asset_id=asset.id))
        
        asset.name = request.form['name']
        asset.serial_number = request.form['serial']
        asset.type = request.form['type']
        asset.status = request.form['status']
        db.session.commit()
        flash('Asset updated.', 'success')
        return redirect(url_for('asset_list'))
    return render_template('edit_asset.html', asset=asset)

@app.route('/assets/unassign/<int:asset_id>')
@login_required
@admin_required
def unassign_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    
    # Revoke the active approved request (if any) and make asset available again
    active_request = next(
        (req for req in asset.requests if req.status == 'approved'),
        None
    )
    if active_request:
        active_request.status = 'revoked'
    asset.status = 'available'
    db.session.commit()
    flash(f"Asset '{asset.name}' has been unassigned and is now available.", 'info')
    return redirect(url_for('asset_list'))

@app.route('/assets/delete/<int:asset_id>')
@login_required
@admin_required
def delete_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    if asset.status == 'assigned':
        # Redirect to unassign first instead of deletion if asset is in use
        flash(
            f"Asset '{asset.name}' is currently assigned. Unassign it first to delete.",
            'warning'
        )
        return redirect(url_for('unassign_asset', asset_id=asset.id))

    db.session.delete(asset)
    db.session.commit()
    flash('Asset deleted.', 'success')
    return redirect(url_for('asset_list'))

# Create database tables at first run
with app.app_context():
    db.create_all()

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

