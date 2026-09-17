import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-change-me')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'mediabox.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'webm', 'ogg', 'wav', 'flac', 'mkv', 'avi', 'mov'}
    ALLOWED_MIME_TYPES = {
        'audio/mpeg', 'audio/mp4', 'audio/ogg', 'audio/wav', 'audio/flac',
        'audio/x-flac', 'audio/webm', 'audio/x-wav',
        'video/mp4', 'video/webm', 'video/ogg', 'video/x-matroska',
        'video/x-msvideo', 'video/quicktime',
    }
    VIDEO_EXTENSIONS = {'mp4', 'webm', 'mkv', 'avi', 'mov'}
    ITEMS_PER_PAGE = 12
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
