from collections import defaultdict
from datetime import timedelta
import logging
import os
from logging.handlers import RotatingFileHandler


try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - Vercel/local env vars can still work without python-dotenv
    load_dotenv = None


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

if load_dotenv is not None:
    load_dotenv(os.path.join(BASE_DIR, '.env'))

PUBLIC_ROOT = os.path.join(BASE_DIR, 'public')
STATIC_ROOT = os.path.join(PUBLIC_ROOT, 'static')


def normalize_database_url(raw_url):
    """Return a SQLAlchemy-compatible Postgres URL for Supabase/Vercel."""
    url = (raw_url or '').strip()
    if not url:
        return ''
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    if url.startswith('postgresql://') and 'sslmode=' not in url.lower():
        separator = '&' if '?' in url else '?'
        url = f'{url}{separator}sslmode=require'
    return url


DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'app.db'))
BACKFILL_MARKER = os.environ.get(
    'BACKFILL_MARKER_PATH',
    os.path.join(BASE_DIR, '.backfill_user_locations_once'),
)
UPLOAD_FOLDER = os.environ.get(
    'UPLOAD_FOLDER',
    os.path.join(STATIC_ROOT, 'uploads'),
)
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_ASSET_IMAGES = 3
MAX_IMAGE_UPLOAD_SIZE = int(os.environ.get('MAX_IMAGE_UPLOAD_SIZE', 8 * 1024 * 1024))
MAX_REQUEST_SIZE = int(os.environ.get('MAX_REQUEST_SIZE', 32 * 1024 * 1024))
SERVICE_INVOICE_MAP = os.environ.get(
    'SERVICE_INVOICE_MAP_PATH',
    os.path.join(BASE_DIR, 'service_invoice_images.json'),
)
SERVICE_INVOICE_MARKER = '[[service_invoice_image:'
LOG_DIR = os.environ.get('LOG_DIR', os.path.join(BASE_DIR, 'logs'))
APP_LOG_PATH = os.environ.get('APP_LOG_PATH', os.path.join(LOG_DIR, 'app.log'))
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip().rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', '').strip()
SUPABASE_STORAGE_PREFIX = os.environ.get('SUPABASE_STORAGE_PREFIX', 'uploads').strip('/ ')
CSRF_SESSION_KEY = '_csrf_token'
CSRF_FORM_FIELD = 'csrf_token'
CSRF_HEADER_NAMES = ('X-CSRFToken', 'X-CSRF-Token')
UNSAFE_HTTP_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
LOGIN_RATE_LIMIT = (7, 300)
SENSITIVE_RATE_LIMIT = (20, 300)
RATE_LIMIT_BUCKETS = defaultdict(list)
VERCEL_ENVIRONMENT = bool(os.environ.get('VERCEL'))


def configure_app(flask_app):
    _secret_key = os.environ.get('SECRET_KEY')
    if not _secret_key:
        raise RuntimeError('SECRET_KEY must be set.')
    flask_app.config['SECRET_KEY'] = _secret_key

    raw_database_url = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
    database_url = normalize_database_url(raw_database_url)
    database_url_invalid = bool(database_url and database_url.startswith(('http://', 'https://')))
    flask_app.config['DATABASE_URL_INVALID'] = database_url_invalid

    if os.environ.get('VERCEL') and not database_url:
        raise RuntimeError(
            'DATABASE_URL must be set on Vercel. Use the Supabase PostgreSQL connection string, not SQLite.'
        )
    if os.environ.get('VERCEL') and database_url_invalid:
        raise RuntimeError(
            'DATABASE_URL must be a PostgreSQL connection string, not the Supabase project URL.'
        )
    if database_url and not database_url_invalid:
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': int(os.environ.get('SQLALCHEMY_POOL_RECYCLE', '180')),
            'pool_size': int(os.environ.get('SQLALCHEMY_POOL_SIZE', '1')),
            'max_overflow': int(os.environ.get('SQLALCHEMY_MAX_OVERFLOW', '4')),
            'pool_timeout': int(os.environ.get('SQLALCHEMY_POOL_TIMEOUT', '10')),
        }
    else:
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    flask_app.config['SERVICE_INVOICE_MAP'] = SERVICE_INVOICE_MAP
    flask_app.config['MAX_IMAGE_UPLOAD_SIZE'] = MAX_IMAGE_UPLOAD_SIZE
    flask_app.config['MAX_CONTENT_LENGTH'] = MAX_REQUEST_SIZE
    flask_app.config['SESSION_COOKIE_HTTPONLY'] = True
    flask_app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    flask_app.config['SESSION_COOKIE_SECURE'] = os.environ.get('APP_ENV') == 'production'
    flask_app.config['PREFERRED_URL_SCHEME'] = os.environ.get('PREFERRED_URL_SCHEME', 'http')
    server_name = os.environ.get('SERVER_NAME')
    if server_name:
        flask_app.config['SERVER_NAME'] = server_name
    flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)


def configure_app_logging(flask_app):
    if flask_app.logger.handlers:
        return
    if VERCEL_ENVIRONMENT:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))
        handler.setLevel(logging.INFO)
        flask_app.logger.addHandler(handler)
        flask_app.logger.setLevel(logging.INFO)
        return
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = RotatingFileHandler(APP_LOG_PATH, maxBytes=1_000_000, backupCount=5, encoding='utf-8')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    handler.setLevel(logging.INFO)
    flask_app.logger.addHandler(handler)
    flask_app.logger.setLevel(logging.INFO)
