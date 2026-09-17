import os
import string
import random
import bcrypt
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app, request
from flask_login import login_required, current_user, login_user
from models import db, User, Media
from utils import format_size
from userstore import load_store, delete_user_data

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_required
def panel():
    users = User.query.order_by(User.created_at.desc()).all()
    media_list = Media.query.order_by(Media.created_at.desc()).all()
    total_size = sum(m.file_size for m in media_list)
    store = load_store()
    return render_template(
        'admin.html', users=users, media_list=media_list,
        total_size=total_size, format_size=format_size, store=store
    )


@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Nie mozesz usunac swojego konta.', 'error')
        return redirect(url_for('admin.panel'))
    user = User.query.get_or_404(user_id)
    username = user.username
    for media in user.media.all():
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], media.filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    db.session.delete(user)
    db.session.commit()
    delete_user_data(username)
    flash(f'Uzytkownik {username} zostal usuniety calkowicie (baza, pliki oraz wpisy w users.json).', 'info')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/delete-media/<int:media_id>', methods=['POST'])
@admin_required
def delete_media(media_id):
    media = Media.query.get_or_404(media_id)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], media.filename)
    if os.path.isfile(filepath):
        os.remove(filepath)
    db.session.delete(media)
    db.session.commit()
    flash('Plik zostal usuniety.', 'info')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/ban/<int:user_id>', methods=['POST'])
@admin_required
def ban_user(user_id):
    if user_id == current_user.id:
        flash('Nie mozesz zbanowac siebie.', 'error')
        return redirect(url_for('admin.panel'))
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Nie mozna zbanowac administratora. Najpierw zmien role w users.json.', 'error')
        return redirect(url_for('admin.panel'))
    user.is_banned = not user.is_banned
    db.session.commit()
    status = 'zbanowany' if user.is_banned else 'odbanowany'
    flash(f'{user.username} zostal {status}.', 'info')
    return redirect(url_for('admin.panel'))


def owner_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'OWNER':
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@owner_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Nie mozesz zresetowac wlasnego hasla z tego poziomu.', 'error')
        return redirect(url_for('admin.panel'))
    
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        chars = string.ascii_letters + string.digits
        new_password = ''.join(random.choice(chars) for _ in range(12))
        
    pw_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password_hash = pw_hash
    user.failed_logins = 0
    user.locked_until = None
    db.session.commit()
    
    flash(f'Haslo dla {user.username} zostalo zmienione na: {new_password}', 'info')
    return redirect(url_for('admin.panel'))


@admin_bp.route('/impersonate/<int:user_id>', methods=['POST'])
@owner_required
def impersonate(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Juz jestes zalogowany jako ty.', 'error')
        return redirect(url_for('admin.panel'))
    
    login_user(user)
    flash(f'Zalogowano jako {user.username}.', 'info')
    return redirect(url_for('media.dashboard'))
