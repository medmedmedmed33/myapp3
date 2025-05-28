from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from models import Admin, Coach

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Admin):
            flash('Accès refusé. Droits administrateur requis.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def coach_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not isinstance(current_user, Coach):
            flash('Accès refusé. Droits entraîneur requis.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function 