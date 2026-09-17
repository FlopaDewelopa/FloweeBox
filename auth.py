import re
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
import bcrypt
from models import db, User
from userstore import register_user, update_login

auth_bp = Blueprint('auth', __name__)

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,80}$')


EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('media.index'))
    
    username = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not USERNAME_RE.match(username):
            flash('Nazwa: 3-80 znakow, tylko litery, cyfry, podkreslnik.', 'error')
            return render_template('register.html', username=username)
            
        if len(password) < 8 or len(password) > 128:
            flash('Haslo musi miec 8-128 znakow.', 'error')
            return render_template('register.html', username=username)
            
        if User.query.filter_by(username=username).first():
            flash('Nazwa uzytkownika jest juz zajeta.', 'error')
            return render_template('register.html', username=username)
            
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(username=username, password_hash=pw_hash)
        db.session.add(user)
        db.session.commit()
        register_user(username, request.remote_addr)
        login_user(user)
        return redirect(url_for('media.dashboard'))
    return render_template('register.html', username=username)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('media.index'))
        
    username = ''
    if request.method == 'POST':
        username = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        if user:
            if user.is_banned:
                flash('Konto zostalo zablokowane przez administratora.', 'error')
                return render_template('login.html', login_id=username)
            now = datetime.now(timezone.utc)
            if user.locked_until and user.locked_until > now:
                remaining = (user.locked_until - now).seconds // 60 + 1
                flash(f'Konto zablokowane. Sprobuj za {remaining} min.', 'error')
                return render_template('login.html', login_id=username)
            if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                user.failed_logins = 0
                user.locked_until = None
                db.session.commit()
                update_login(user.username, request.remote_addr)
                login_user(user)
                next_page = request.args.get('next', '')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('media.index'))
            user.failed_logins = (user.failed_logins or 0) + 1
            max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
            if user.failed_logins >= max_attempts:
                lockout = current_app.config.get('LOCKOUT_MINUTES', 15)
                user.locked_until = now + timedelta(minutes=lockout)
                user.failed_logins = 0
                db.session.commit()
                flash(f'Zbyt wiele prob. Konto zablokowane na {lockout} min.', 'error')
            else:
                db.session.commit()
                flash('Nieprawidlowy login lub haslo.', 'error')
        else:
            flash('Nieprawidlowy login lub haslo.', 'error')
        return render_template('login.html', login_id=username)
    return render_template('login.html', login_id=username)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('media.index'))
