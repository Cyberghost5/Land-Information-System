from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from models import User

def get_current_user():
    """Returns the currently active user in the session (or impersonated user)."""
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def is_impersonating():
    """Returns True if an admin is currently impersonating another user."""
    return bool(session.get('impersonator_admin_id'))

def get_impersonator_admin():
    """Returns the original admin user if an impersonation session is active."""
    admin_id = session.get('impersonator_admin_id')
    if admin_id:
        return User.query.get(admin_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def verified_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('login'))
        if not user.is_verified:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Email not verified. Please verify your email first.'}), 403
            flash('Your email address has not been verified yet. Please check your inbox.', 'warning')
            return redirect(url_for('verification_pending'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        # If impersonating, the user session acts as the target user, but the original admin can still return
        if not user or not user.is_admin():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Administrator privileges required.'}), 403
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('user_map'))
        return f(*args, **kwargs)
    return decorated_function
