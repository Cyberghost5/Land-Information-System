import os
import json
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify
)
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

from models import db, User, Parcel, SavedParcel
from email_utils import (
    generate_verification_token, confirm_verification_token,
    send_verification_email, LATEST_VERIFICATION_LINKS
)
from auth import (
    get_current_user, is_impersonating, get_impersonator_admin,
    login_required, verified_required, admin_required
)
from seed import seed_database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ogun-state-lis-super-secure-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(BASE_DIR, 'lis.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db.init_app(app)

# Inject current user state into all Jinja templates
@app.context_processor
def inject_user_context():
    user = get_current_user()
    return {
        'current_user': user,
        'is_impersonating': is_impersonating(),
        'impersonator_admin': get_impersonator_admin(),
        'now': datetime.utcnow()
    }

# ============================================================================
# PUBLIC & LANDING ROUTES
# ============================================================================

@app.route('/')
def index():
    """Public landing page."""
    user = get_current_user()
    if user:
        if user.is_admin() and not is_impersonating():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_map'))
    return render_template('landing.html')

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with full details and SMTP verification trigger."""
    if get_current_user():
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validations
        if not (full_name and email and phone and address and password):
            flash('All fields are required. Please complete the registration form.', 'danger')
            return render_template('auth/register.html', form=request.form)

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return render_template('auth/register.html', form=request.form)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', form=request.form)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        # Create unverified user
        new_user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            role='user',
            is_verified=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Generate verification token & send email
        token = generate_verification_token(new_user.email, app.config['SECRET_KEY'])
        verification_url = url_for('verify_email', token=token, _external=True)
        send_verification_email(new_user.email, new_user.full_name, verification_url)

        session['pending_verification_email'] = new_user.email
        flash(f'Account registered! A verification link has been dispatched to {new_user.email}. Please verify your email to activate your account.', 'success')
        return redirect(url_for('verification_pending'))

    return render_template('auth/register.html')

@app.route('/verify-email/<token>')
def verify_email(token):
    """Verifies user email via URL token."""
    email = confirm_verification_token(token, app.config['SECRET_KEY'], expiration=86400)
    if not email:
        flash('The verification link is invalid or has expired (24 hours limit). Please request a new one.', 'danger')
        return redirect(url_for('resend_verification'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User account not found.', 'danger')
        return redirect(url_for('register'))

    if user.is_verified:
        flash('Your email is already verified. You can log in directly.', 'info')
        return redirect(url_for('login'))

    user.is_verified = True
    db.session.commit()

    flash('Congratulations! Your email has been verified successfully. You may now log in to access the system.', 'success')
    return redirect(url_for('login'))

@app.route('/verification-pending')
def verification_pending():
    """Notice page displayed after registration awaiting email verification."""
    email = session.get('pending_verification_email')
    latest_link = LATEST_VERIFICATION_LINKS.get(email) if email else None
    return render_template('auth/verification_pending.html', email=email, dev_link=latest_link)

@app.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Allows resending an activation link if expired or lost."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('No account found with that email address.', 'danger')
            return render_template('auth/resend_verification.html')

        if user.is_verified:
            flash('This account is already verified. Please proceed to log in.', 'info')
            return redirect(url_for('login'))

        token = generate_verification_token(user.email, app.config['SECRET_KEY'])
        verification_url = url_for('verify_email', token=token, _external=True)
        send_verification_email(user.email, user.full_name, verification_url)

        session['pending_verification_email'] = user.email
        flash(f'A fresh verification link has been dispatched to {user.email}.', 'success')
        return redirect(url_for('verification_pending'))

    return render_template('auth/resend_verification.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User and Administrator login."""
    if get_current_user():
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password. Please verify your credentials.', 'danger')
            return render_template('auth/login.html')

        if not user.is_verified:
            session['pending_verification_email'] = user.email
            flash('Your email address has not been verified yet. Please check your inbox or resend the verification link.', 'warning')
            return redirect(url_for('verification_pending'))

        # Log in user
        session['user_id'] = user.id
        session.pop('impersonator_admin_id', None)  # Clear any old impersonation state

        flash(f'Welcome back, {user.full_name}!', 'success')
        if user.is_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_map'))

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    """Logs out the active session."""
    session.clear()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('index'))

# ============================================================================
# USER APPLICATION & MAP ROUTES
# ============================================================================

@app.route('/map')
@login_required
@verified_required
def user_map():
    """
    Cadastral Map Portal for authenticated users.
    NOTE: Initial map load is clean (no parcels pre-rendered, unclickable by default).
    Only searched parcels will be loaded and displayed on the map.
    """
    return render_template('map.html')

@app.route('/saved-parcels')
@login_required
@verified_required
def saved_parcels():
    """Dedicated management page for parcels saved by the user."""
    user = get_current_user()
    saved_items = SavedParcel.query.filter_by(user_id=user.id).order_by(SavedParcel.saved_at.desc()).all()
    return render_template('saved_parcels.html', saved_items=saved_items)

# ============================================================================
# SPATIAL PARCEL REST API ROUTES
# ============================================================================

@app.route('/api/parcels/search/<parcel_id>', methods=['GET'])
@login_required
@verified_required
def search_parcel(parcel_id):
    """
    Searches for a parcel by ID in the database.
    Returns ONLY the matching parcel(s) as a GeoJSON FeatureCollection.
    No pre-loaded suggestions are returned.
    """
    cleaned_id = parcel_id.strip()
    
    # 1. Exact match (case-insensitive)
    matched_parcel = Parcel.query.filter(
        db.func.lower(Parcel.parcel_id) == cleaned_id.lower()
    ).first()

    matched_parcels = [matched_parcel] if matched_parcel else []

    # 2. Fallback to partial match if no exact match
    if not matched_parcels:
        matched_parcels = Parcel.query.filter(
            Parcel.parcel_id.ilike(f"%{cleaned_id}%")
        ).limit(5).all()

    if not matched_parcels:
        return jsonify({
            'type': 'FeatureCollection',
            'features': [],
            'found': False,
            'message': f"Parcel ID '{parcel_id}' was not found in the cadastral registry."
        }), 404

    features = [p.to_geojson_feature() for p in matched_parcels]

    # Check if current user has already saved this parcel
    user = get_current_user()
    saved_ids = set()
    if user:
        user_saved = SavedParcel.query.filter_by(user_id=user.id).all()
        saved_ids = {sp.parcel_id.lower() for sp in user_saved}

    for feat in features:
        pid = feat.get('properties', {}).get('Parcel_ID', '')
        feat['properties']['is_saved'] = (pid.lower() in saved_ids)

    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
        'found': True,
        'count': len(features)
    }), 200

@app.route('/api/parcels/save', methods=['POST'])
@login_required
@verified_required
def save_parcel():
    """Saves a parcel to the logged-in user's portfolio."""
    data = request.get_json(silent=True) or request.form
    parcel_id = data.get('parcel_id', '').strip()
    notes = data.get('notes', '').strip()

    if not parcel_id:
        return jsonify({'error': 'Parcel ID is required.'}), 400

    user = get_current_user()
    existing = SavedParcel.query.filter_by(user_id=user.id, parcel_id=parcel_id).first()
    if existing:
        return jsonify({'success': True, 'message': 'Parcel is already saved.', 'id': existing.id}), 200

    # Verify parcel exists in DB
    parcel = Parcel.query.filter(db.func.lower(Parcel.parcel_id) == parcel_id.lower()).first()
    if not parcel:
        return jsonify({'error': f"Parcel '{parcel_id}' not found in registry."}), 404

    saved = SavedParcel(user_id=user.id, parcel_id=parcel.parcel_id, notes=notes)
    db.session.add(saved)
    db.session.commit()

    return jsonify({'success': True, 'message': f'Parcel {parcel.parcel_id} saved successfully.', 'id': saved.id}), 201

@app.route('/api/parcels/saved/<int:saved_id>', methods=['DELETE'])
@login_required
@verified_required
def delete_saved_parcel(saved_id):
    """Removes a saved parcel from the user's portfolio."""
    user = get_current_user()
    saved = SavedParcel.query.filter_by(id=saved_id, user_id=user.id).first()
    if not saved:
        return jsonify({'error': 'Saved parcel not found.'}), 404

    db.session.delete(saved)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Parcel removed from your saved list.'}), 200

# ============================================================================
# ADMINISTRATOR ROUTES & IMPERSONATION
# ============================================================================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Administrator Management Dashboard."""
    users = User.query.order_by(User.created_at.desc()).all()
    parcels = Parcel.query.order_by(Parcel.id.desc()).all()
    parcels_count = len(parcels)
    users_count = len(users)
    saved_count = SavedParcel.query.count()
    return render_template(
        'admin/dashboard.html',
        users=users,
        parcels=parcels,
        parcels_count=parcels_count,
        users_count=users_count,
        saved_count=saved_count
    )

@app.route('/admin/parcels/add', methods=['POST'])
@login_required
@admin_required
def admin_add_parcel():
    """Administrator adds a new cadastral parcel."""
    pid = request.form.get('parcel_id', '').strip()
    if not pid:
        flash('Parcel ID is required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    existing = Parcel.query.filter(db.func.lower(Parcel.parcel_id) == pid.lower()).first()
    if existing:
        flash(f"A parcel with ID '{pid}' already exists.", 'danger')
        return redirect(url_for('admin_dashboard'))

    owner = request.form.get('owner', '').strip()
    landuse = request.form.get('landuse', 'Residential').strip()
    status = request.form.get('status', 'Verified').strip()
    location = request.form.get('location', 'Abeokuta').strip()
    lga = request.form.get('lga', 'Abeokuta South').strip()
    title_number = request.form.get('title_number', '').strip()
    survey_plan = request.form.get('survey_plan', '').strip()
    
    try:
        area = float(request.form.get('area', 0.0))
    except ValueError:
        area = 0.0

    geometry_str = request.form.get('geometry_json', '').strip()
    if not geometry_str:
        # Default placeholder polygon if none provided
        geometry_str = json.dumps({
            "type": "Polygon",
            "coordinates": [[[539600.0, 790200.0], [539650.0, 790200.0], [539650.0, 790250.0], [539600.0, 790250.0], [539600.0, 790200.0]]]
        })
    else:
        try:
            json.loads(geometry_str)
        except Exception as e:
            flash(f"Invalid Geometry JSON: {e}", 'danger')
            return redirect(url_for('admin_dashboard'))

    properties = {
        'Parcel_ID': pid,
        'Par_Owner': owner,
        'landuse': landuse,
        'Area': area,
        'Status': status,
        'Location': location,
        'LGA': lga,
        'State': 'Ogun',
        'Country': 'Nigeria',
        'Title_numb': title_number or 'Pending',
        'Surv_plan': survey_plan or 'Available',
        'Rec_date': datetime.utcnow().strftime('%Y-%m-%dT00:00:00Z')
    }

    new_parcel = Parcel(
        parcel_id=pid,
        owner=owner,
        landuse=landuse,
        area=area,
        status=status,
        location=location,
        lga=lga,
        state='Ogun',
        country='Nigeria',
        title_number=title_number,
        survey_plan=survey_plan,
        rec_date=properties['Rec_date'],
        properties_json=json.dumps(properties),
        geometry_json=geometry_str
    )
    db.session.add(new_parcel)
    db.session.commit()

    flash(f"Cadastral Parcel '{pid}' successfully created and added to the registry.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/parcels/edit/<int:parcel_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_parcel(parcel_id):
    """Administrator updates an existing cadastral parcel."""
    parcel = Parcel.query.get(parcel_id)
    if not parcel:
        flash('Parcel not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    parcel.owner = request.form.get('owner', parcel.owner).strip()
    parcel.landuse = request.form.get('landuse', parcel.landuse).strip()
    parcel.status = request.form.get('status', parcel.status).strip()
    parcel.location = request.form.get('location', parcel.location).strip()
    parcel.lga = request.form.get('lga', parcel.lga).strip()
    parcel.title_number = request.form.get('title_number', parcel.title_number).strip()
    parcel.survey_plan = request.form.get('survey_plan', parcel.survey_plan).strip()

    try:
        parcel.area = float(request.form.get('area', parcel.area or 0.0))
    except ValueError:
        pass

    geometry_str = request.form.get('geometry_json', '').strip()
    if geometry_str:
        try:
            json.loads(geometry_str)
            parcel.geometry_json = geometry_str
        except Exception as e:
            flash(f"Invalid Geometry JSON: {e}", 'danger')
            return redirect(url_for('admin_dashboard'))

    # Update properties JSON
    props = parcel.get_properties()
    props['Par_Owner'] = parcel.owner
    props['landuse'] = parcel.landuse
    props['Status'] = parcel.status
    props['Area'] = parcel.area
    props['Location'] = parcel.location
    props['LGA'] = parcel.lga
    props['Title_numb'] = parcel.title_number
    props['Surv_plan'] = parcel.survey_plan
    parcel.properties_json = json.dumps(props)

    db.session.commit()
    flash(f"Parcel '{parcel.parcel_id}' updated successfully.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/parcels/delete/<int:parcel_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_parcel(parcel_id):
    """Administrator deletes a parcel from the registry."""
    parcel = Parcel.query.get(parcel_id)
    if not parcel:
        flash('Parcel not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    pid = parcel.parcel_id
    # Remove any bookmarks for this parcel
    SavedParcel.query.filter_by(parcel_id=pid).delete()
    db.session.delete(parcel)
    db.session.commit()

    flash(f"Parcel '{pid}' has been permanently deleted from the registry.", 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/parcels/import', methods=['POST'])
@login_required
@admin_required
def admin_import_parcels():
    """Administrator imports parcels from an uploaded GeoJSON file."""
    if 'file' not in request.files:
        flash('No file selected for upload.', 'danger')
        return redirect(url_for('admin_dashboard'))

    file = request.files['file']
    if not file or file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if not (file.filename.lower().endswith('.geojson') or file.filename.lower().endswith('.json')):
        flash('Invalid file format. Please upload a .geojson or .json file.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        content = json.load(file)
        features = content.get('features', []) if isinstance(content, dict) else content
        if not isinstance(features, list):
            flash('Invalid GeoJSON structure: Expected a FeatureCollection or list of features.', 'danger')
            return redirect(url_for('admin_dashboard'))

        added_count = 0
        updated_count = 0

        for feat in features:
            props = feat.get('properties', {})
            geom = feat.get('geometry', {})
            pid = props.get('Parcel_ID')
            if not pid or not geom:
                continue

            clean_pid = str(pid).strip()
            existing = Parcel.query.filter(db.func.lower(Parcel.parcel_id) == clean_pid.lower()).first()

            if existing:
                existing.owner = props.get('Par_Owner', existing.owner)
                existing.landuse = props.get('landuse', existing.landuse)
                existing.area = props.get('Area', existing.area)
                existing.status = props.get('Status', existing.status)
                existing.location = props.get('Location', existing.location)
                existing.lga = props.get('LGA', existing.lga)
                existing.title_number = props.get('Title_numb', existing.title_number)
                existing.survey_plan = props.get('Surv_plan', existing.survey_plan)
                existing.rec_date = props.get('Rec_date', existing.rec_date)
                existing.properties_json = json.dumps(props)
                existing.geometry_json = json.dumps(geom)
                updated_count += 1
            else:
                new_p = Parcel(
                    parcel_id=clean_pid,
                    owner=props.get('Par_Owner'),
                    landuse=props.get('landuse', 'Residential'),
                    area=props.get('Area', 0.0),
                    status=props.get('Status', 'Unverified'),
                    location=props.get('Location', 'Abeokuta'),
                    lga=props.get('LGA', 'Abeokuta South'),
                    state=props.get('State', 'Ogun'),
                    country=props.get('Country', 'Nigeria'),
                    title_number=props.get('Title_numb'),
                    survey_plan=props.get('Surv_plan'),
                    rec_date=props.get('Rec_date'),
                    properties_json=json.dumps(props),
                    geometry_json=json.dumps(geom)
                )
                db.session.add(new_p)
                added_count += 1

        db.session.commit()
        flash(f"GeoJSON Import Completed: {added_count} new parcels imported, {updated_count} existing parcels updated.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to process GeoJSON file: {e}", 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/toggle-role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_role(user_id):
    """Toggles user role between user and admin."""
    target_user = User.query.get(user_id)
    if not target_user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    current = get_current_user()
    if target_user.id == current.id:
        flash('You cannot modify your own administrative role.', 'warning')
        return redirect(url_for('admin_dashboard'))

    new_role = 'admin' if target_user.role == 'user' else 'user'
    target_user.role = new_role
    db.session.commit()

    flash(f"Role for '{target_user.full_name}' updated to '{new_role}'.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/impersonate/<int:target_user_id>', methods=['POST'])
@login_required
@admin_required
def impersonate_user(target_user_id):
    """Admin impersonates a specific user to view the app as them."""
    target_user = User.query.get(target_user_id)
    if not target_user:
        flash('Target user not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Store original admin ID if not already impersonating
    if 'impersonator_admin_id' not in session:
        session['impersonator_admin_id'] = session['user_id']

    session['user_id'] = target_user.id
    flash(f"Impersonation active: You are now viewing the system as '{target_user.full_name}' ({target_user.email}).", 'info')
    return redirect(url_for('user_map'))

@app.route('/admin/stop-impersonating', methods=['POST'])
def stop_impersonating():
    """Ends user impersonation and restores the administrator session."""
    impersonator_id = session.pop('impersonator_admin_id', None)
    if impersonator_id:
        session['user_id'] = impersonator_id
        flash('Exited impersonation mode. Restored administrator session.', 'success')
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('index'))

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

with app.app_context():
    seed_database(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
