import os
import mimetypes
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user, logout_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from models import db, User


def create_app():
    app = Flask(__name__)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    app.config.from_object(Config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    mimetypes.add_type('audio/flac', '.flac')
    mimetypes.add_type('video/x-matroska', '.mkv')

    db.init_app(app)
    CSRFProtect(app)

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour"],
        storage_uri="memory://"
    )

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Zaloguj sie aby uzyskac dostep.'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from auth import auth_bp
    from media import media_bp
    from admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(admin_bp)
    limiter.limit("10 per minute")(auth_bp)

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response

    @app.before_request
    def check_banned():
        if current_user.is_authenticated and current_user.is_banned:
            logout_user()
            flash('Konto zostalo zablokowane przez administratora.', 'error')
            return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404, message='Nie znaleziono strony.'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', code=403, message='Brak dostepu.'), 403

    @app.errorhandler(413)
    def too_large(e):
        return render_template('error.html', code=413, message='Plik jest za duzy. Maksymalny rozmiar to 500 MB.'), 413

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template('error.html', code=429, message='Zbyt wiele zapytan. Sprobuj ponownie pozniej.'), 429

    with app.app_context():
        db.create_all()
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'users' in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns('users')]
            for col, ddl in [
                ('is_banned', 'ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0'),
                ('failed_logins', 'ALTER TABLE users ADD COLUMN failed_logins INTEGER DEFAULT 0'),
                ('locked_until', 'ALTER TABLE users ADD COLUMN locked_until DATETIME'),
            ]:
                if col not in cols:
                    with db.engine.begin() as conn:
                        conn.execute(text(ddl))
        if 'media' in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns('media')]
            if 'share_token' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(text('ALTER TABLE media ADD COLUMN share_token VARCHAR(64)'))

    return app


if __name__ == '__main__':
    application = create_app()
    try:
        from waitress import serve
        print('FloweeBox: http://127.0.0.1:5000')
        serve(application, host='127.0.0.1', port=5000, threads=4)
    except ImportError:
        application.run(host='127.0.0.1', port=5000, debug=False)
