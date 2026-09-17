from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_banned = db.Column(db.Boolean, default=False)
    failed_logins = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    media = db.relationship('Media', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_admin(self):
        from userstore import is_admin_or_owner
        return is_admin_or_owner(self.username)

    @property
    def role(self):
        from userstore import get_role
        return get_role(self.username)


class Media(db.Model):
    __tablename__ = 'media'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=True, index=True)
    media_type = db.Column(db.String(10), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    share_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
