import os
import logging

from flask import Flask, flash, redirect, url_for, request, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db
from models import User, Admin, Coach
from decorators import admin_required, coach_required

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///football_tournament.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if isinstance(user, Admin):
                return redirect(url_for('admin.tournament_list'))
            elif isinstance(user, Coach):
                return redirect(url_for('coach.team_dashboard'))
            else:
                return redirect(next_page or url_for('index'))
        flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Enregistrement des blueprints
from routes.admin import admin_bp
from routes.coach import coach_bp

app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(coach_bp, url_prefix='/coach')

with app.app_context():
    # Import models here to ensure they are registered with SQLAlchemy
    from models import *  # noqa: F401
    db.create_all()
    
    # Créer un admin par défaut si aucun n'existe
    if not Admin.query.first():
        admin = Admin(username='admin', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if isinstance(current_user, Admin):
            return redirect(url_for('admin.tournament_list'))
        elif isinstance(current_user, Coach):
            return redirect(url_for('coach.team_dashboard'))
    return 'Bienvenue sur Flask Class Manager. <a href="/login">Se connecter</a>'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
