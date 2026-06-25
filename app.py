import time
from collections import defaultdict, deque
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import case

from config import Config, validate_config
from extensions import db, login_manager, csrf
from forms import RegisterForm, LoginForm, RequestForm, AssetForm, EditAssetForm
from models import User, Asset, Request as AssetRequest

# ---------------- APP SETUP ----------------

app = Flask(__name__)
app.config.from_object(Config)
validate_config(app)

# Initialise Flask extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
login_manager.login_view = 'login'  # Redirect unauthenticated users here

login_attempts = defaultdict(deque)


def login_rate_limit_key(username):
    remote_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    remote_addr = remote_addr.split(",")[0].strip() if remote_addr else "unknown"
    return f"{remote_addr}:{username.strip().lower()}"


def recent_login_failures(key):
    now = time.monotonic()
    window = app.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"]
    attempts = login_attempts[key]
    while attempts and now - attempts[0] > window:
        attempts.popleft()
    return attempts


def is_login_rate_limited(key):
    return len(recent_login_failures(key)) >= app.config["LOGIN_RATE_LIMIT_ATTEMPTS"]


def record_login_failure(key):
    recent_login_failures(key).append(time.monotonic())


def clear_login_failures(key):
    login_attempts.pop(key, None)


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdn.jsdelivr.net data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'",
    )
    if app.config["SESSION_COOKIE_SECURE"]:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


def active_assignment_for(asset):
    return next((req for req in asset.requests if req.status == 'approved'), None)


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
            form.username.errors.append('Username already exists.')
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html', form=form)
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
        rate_limit_key = login_rate_limit_key(form.username.data)
        if is_login_rate_limited(rate_limit_key):
            app.logger.warning(
                "login_rate_limited username=%s remote_addr=%s",
                form.username.data,
                request.remote_addr,
            )
            flash('Too many failed login attempts. Please try again later.', 'danger')
            return render_template('login.html', form=form), 429

        user = User.query.filter_by(username=form.username.data).first()
        # Verify password using hash
        if user and check_password_hash(user.password, form.password.data):
            clear_login_failures(rate_limit_key)
            login_user(user)
            app.logger.info("login_success username=%s", user.username)
            flash(f'Welcome, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            record_login_failure(rate_limit_key)
            app.logger.warning(
                "login_failed username=%s remote_addr=%s",
                form.username.data,
                request.remote_addr,
            )
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout', methods=['POST'])
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

        pending_request = AssetRequest.query.filter_by(
            user_id=current_user.id,
            asset_id=asset.id,
            status='pending'
        ).first()
        if pending_request:
            flash('You already have a pending request for this asset.', 'warning')
            return redirect(url_for('dashboard'))

        new_request = AssetRequest(
            user_id=current_user.id,
            asset_id=asset.id,
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

@app.route('/admin/approve/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    # Only admin can approve
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    asset_request = AssetRequest.query.get_or_404(request_id)
    asset = Asset.query.get_or_404(asset_request.asset_id)

    if asset_request.status != 'pending':
        flash('Only pending requests can be approved.', 'warning')
        return redirect(url_for('admin'))

    if asset.status != 'available':
        flash('This asset is no longer available for approval.', 'danger')
        return redirect(url_for('admin'))

    asset_request.status = 'approved'
    asset.status = 'assigned'

    db.session.commit()
    app.logger.info(
        "admin_approved_request admin=%s request_id=%s asset_id=%s",
        current_user.username,
        asset_request.id,
        asset.id,
    )
    flash('Request approved and asset assigned.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/deny/<int:request_id>', methods=['POST'])
@login_required
def deny_request(request_id):
    # Only admin can deny
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    asset_request = AssetRequest.query.get_or_404(request_id)
    if asset_request.status != 'pending':
        flash('Only pending requests can be denied.', 'warning')
        return redirect(url_for('admin'))

    asset_request.status = 'denied'

    db.session.commit()
    app.logger.info(
        "admin_denied_request admin=%s request_id=%s asset_id=%s",
        current_user.username,
        asset_request.id,
        asset_request.asset_id,
    )
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
    form = AssetForm()
    if form.validate_on_submit():
        # Prevent duplicate serial numbers
        existing_asset = Asset.query.filter_by(serial_number=form.serial.data).first()
        if existing_asset:
            form.serial.errors.append('Asset with that serial number already exists.')
            flash('Asset with that serial number already exists.', 'danger')
            return render_template('add_asset.html', form=form)

        asset = Asset(
            name=form.name.data,
            serial_number=form.serial.data,
            type=form.type.data
        )
        db.session.add(asset)
        db.session.commit()
        app.logger.info(
            "admin_added_asset admin=%s asset_id=%s serial=%s",
            current_user.username,
            asset.id,
            asset.serial_number,
        )
        flash('Asset added.', 'success')
        return redirect(url_for('asset_list'))
    elif form.errors:
        flash('Please correct the errors in the asset form.', 'danger')
    return render_template('add_asset.html', form=form)

@app.route('/assets/edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    form = EditAssetForm()
    if form.validate_on_submit():
        new_serial = form.serial.data
        # Prevent serial number collision with other assets
        existing_asset = Asset.query.filter(Asset.serial_number == new_serial, Asset.id != asset.id).first()
        if existing_asset:
            form.serial.errors.append('Another asset with that serial number already exists.')
            flash('Another asset with that serial number already exists.', 'danger')
            return render_template('edit_asset.html', asset=asset, form=form)

        active_request = active_assignment_for(asset)
        if form.status.data == 'assigned' and not active_request:
            form.status.errors.append('Assign assets by approving a pending request.')
            flash('Assign assets by approving a pending request.', 'danger')
            return render_template('edit_asset.html', asset=asset, form=form)

        asset.name = form.name.data
        asset.serial_number = form.serial.data
        asset.type = form.type.data
        if active_request and form.status.data != 'assigned':
            active_request.status = 'revoked'
        asset.status = form.status.data
        db.session.commit()
        app.logger.info(
            "admin_updated_asset admin=%s asset_id=%s status=%s",
            current_user.username,
            asset.id,
            asset.status,
        )
        flash('Asset updated.', 'success')
        return redirect(url_for('asset_list'))
    elif form.errors:
        flash('Please correct the errors in the asset form.', 'danger')
    else:
        form.name.data = asset.name
        form.serial.data = asset.serial_number
        form.type.data = asset.type
        form.status.data = asset.status
    return render_template('edit_asset.html', asset=asset, form=form)

@app.route('/assets/unassign/<int:asset_id>', methods=['POST'])
@login_required
@admin_required
def unassign_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    
    # Revoke the active approved request (if any) and make asset available again
    active_request = active_assignment_for(asset)
    if active_request:
        active_request.status = 'revoked'
    asset.status = 'available'
    db.session.commit()
    app.logger.info(
        "admin_unassigned_asset admin=%s asset_id=%s",
        current_user.username,
        asset.id,
    )
    flash(f"Asset '{asset.name}' has been unassigned and is now available.", 'info')
    return redirect(url_for('asset_list'))

@app.route('/assets/delete/<int:asset_id>', methods=['POST'])
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
        return redirect(url_for('asset_list'))

    asset_id = asset.id
    db.session.delete(asset)
    db.session.commit()
    app.logger.info(
        "admin_deleted_asset admin=%s asset_id=%s",
        current_user.username,
        asset_id,
    )
    flash('Asset deleted.', 'success')
    return redirect(url_for('asset_list'))

# Create database tables at first run
with app.app_context():
    db.create_all()

# Run the app
if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])

