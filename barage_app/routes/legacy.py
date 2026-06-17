from functools import wraps
from datetime import date, datetime
import hmac
import json
import os
import re
import secrets
import time
from uuid import uuid4
from urllib.parse import quote, unquote

from flask import abort, current_app as app, flash, g, has_app_context, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import Integer, and_, case, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional hardening dependency
    Image = None

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - optional storage dependency
    Client = None
    create_client = None

from barage_app.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    BASE_DIR,
    CSRF_FORM_FIELD,
    CSRF_HEADER_NAMES,
    CSRF_SESSION_KEY,
    LOGIN_RATE_LIMIT,
    MAX_ASSET_IMAGES,
    MAX_IMAGE_UPLOAD_SIZE,
    MAX_REQUEST_SIZE,
    RATE_LIMIT_BUCKETS,
    SERVICE_INVOICE_MAP,
    STATIC_ROOT,
    SENSITIVE_RATE_LIMIT,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_STORAGE_PREFIX,
    SUPABASE_URL,
    UNSAFE_HTTP_METHODS,
    UPLOAD_FOLDER,
    VERCEL_ENVIRONMENT,
)
from barage_app.constants import *  # noqa: F403
from barage_app.extensions import db
from barage_app.models import Asset, AssetHistory, AssetImage, AssetServiceRecord, Location, TransferRequest, User


_ROUTES = []
_BEFORE_REQUESTS = []
_CONTEXT_PROCESSORS = []
_TEMPLATE_FILTERS = []
_ERROR_HANDLERS = []


def route(*args, **kwargs):
    def decorator(view):
        _ROUTES.append((args, kwargs, view))
        return view

    return decorator


def before_request(view):
    _BEFORE_REQUESTS.append(view)
    return view


def context_processor(view):
    _CONTEXT_PROCESSORS.append(view)
    return view


def template_filter(name=None):
    def decorator(view):
        _TEMPLATE_FILTERS.append((name, view))
        return view

    return decorator


def errorhandler(code_or_exception):
    def decorator(view):
        _ERROR_HANDLERS.append((code_or_exception, view))
        return view

    return decorator


def register_routes(flask_app):
    for view in _BEFORE_REQUESTS:
        flask_app.before_request(view)
    for view in _CONTEXT_PROCESSORS:
        flask_app.context_processor(view)
    for name, view in _TEMPLATE_FILTERS:
        flask_app.add_template_filter(view, name)
    for code_or_exception, view in _ERROR_HANDLERS:
        flask_app.register_error_handler(code_or_exception, view)
    for args, kwargs, view in _ROUTES:
        flask_app.add_url_rule(*args, view_func=view, **kwargs)


def configured_service_invoice_map():
    if has_app_context():
        return app.config.get('SERVICE_INVOICE_MAP', SERVICE_INVOICE_MAP)
    return SERVICE_INVOICE_MAP


def configured_upload_folder():
    if has_app_context():
        return app.config.get('UPLOAD_FOLDER', UPLOAD_FOLDER)
    return UPLOAD_FOLDER


def configured_max_request_size():
    if has_app_context():
        return app.config.get('MAX_CONTENT_LENGTH', MAX_REQUEST_SIZE)
    return MAX_REQUEST_SIZE


def load_service_invoice_map():
    invoice_map_path = configured_service_invoice_map()
    if not os.path.exists(invoice_map_path):
        return {}
    try:
        with open(invoice_map_path, 'r', encoding='utf-8') as handle:
            return json.load(handle) or {}
    except Exception:
        return {}


def save_service_invoice_map(data):
    with open(configured_service_invoice_map(), 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def supabase_storage_enabled():
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and SUPABASE_STORAGE_BUCKET)


def ensure_storage_configuration():
    if VERCEL_ENVIRONMENT and not supabase_storage_enabled():
        raise RuntimeError(
            'SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and SUPABASE_STORAGE_BUCKET must be set on Vercel. '
            'Local file uploads are not persistent in Vercel Functions.'
        )
    if (SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY or SUPABASE_STORAGE_BUCKET) and not supabase_storage_enabled():
        return False
    if supabase_storage_enabled() and create_client is None:
        raise RuntimeError('supabase must be installed when Supabase Storage is configured.')
    return True


def build_supabase_storage_public_base_url():
    return f'{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}'


def build_storage_key(category, filename):
    key_parts = [part for part in (SUPABASE_STORAGE_PREFIX, category.strip('/ '), filename) if part]
    return '/'.join(key_parts)


def storage_url_from_key(key):
    base_url = build_supabase_storage_public_base_url()
    return f'{base_url}/{quote(key)}'


def get_supabase_storage_client():
    if not supabase_storage_enabled():
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def save_uploaded_file(uploaded_file, category):
    if not uploaded_file or not getattr(uploaded_file, 'filename', ''):
        return None
    ext = validate_image_upload(uploaded_file)
    stored_name = f'{uuid4().hex}.{ext}'
    if supabase_storage_enabled():
        key = build_storage_key(category, stored_name)
        client = get_supabase_storage_client()
        uploaded_file.stream.seek(0)
        try:
            payload = uploaded_file.stream.read()
            client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                path=key,
                file=payload,
                file_options={
                    'content-type': uploaded_file.mimetype or f'image/{ext}',
                    'x-upsert': 'false',
                },
            )
        except Exception as exc:
            raise ValueError('Грешка при качване на файла към външното хранилище.') from exc
        return storage_url_from_key(key)

    upload_folder = configured_upload_folder()
    os.makedirs(upload_folder, exist_ok=True)
    folder = os.path.join(upload_folder, *[part for part in category.split('/') if part])
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, stored_name)
    uploaded_file.save(file_path)

    static_root = os.path.abspath(app.static_folder or STATIC_ROOT)
    absolute_file_path = os.path.abspath(file_path)
    if absolute_file_path.startswith(static_root):
        relative_static_path = os.path.relpath(absolute_file_path, static_root).replace('\\', '/')
        return f'{app.static_url_path.rstrip("/")}/{relative_static_path}'
    return '/' + os.path.relpath(file_path, BASE_DIR).replace('\\', '/')


def delete_uploaded_file(file_url):
    if not file_url:
        return
    if supabase_storage_enabled():
        prefix = build_supabase_storage_public_base_url() + '/'
        if not file_url.startswith(prefix):
            return
        key = unquote(file_url[len(prefix):])
        client = get_supabase_storage_client()
        try:
            client.storage.from_(SUPABASE_STORAGE_BUCKET).remove([key])
        except Exception:
            app.logger.warning('storage_delete_failed url=%s', file_url)
        return

    absolute_path = resolve_upload_fs_path(file_url)
    if not absolute_path:
        return
    if os.path.exists(absolute_path):
        try:
            os.remove(absolute_path)
        except OSError:
            app.logger.warning('storage_delete_failed path=%s', absolute_path)


def detect_image_type(header_bytes):
    if header_bytes.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if header_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header_bytes.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if header_bytes.startswith(b'RIFF') and header_bytes[8:12] == b'WEBP':
        return 'webp'
    return None


def validate_image_upload(uploaded_file, *, max_size_bytes=MAX_IMAGE_UPLOAD_SIZE):
    if not uploaded_file or not getattr(uploaded_file, 'filename', ''):
        return None

    filename = secure_filename(uploaded_file.filename)
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError('Неподдържан формат на снимка.')

    uploaded_file.stream.seek(0, os.SEEK_END)
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    if file_size > max_size_bytes:
        raise ValueError(f'Снимката е твърде голяма. Максимум {max_size_bytes // (1024 * 1024)} MB.')

    header = uploaded_file.stream.read(512)
    uploaded_file.stream.seek(0)
    detected_type = detect_image_type(header)
    if not detected_type:
        raise ValueError('Файлът не е валидно изображение.')

    if detected_type not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError('Файлът не е поддържано изображение.')
    if ext in {'jpg', 'jpeg'} and detected_type != 'jpg':
        raise ValueError('Разширението на файла не съответства на съдържанието.')
    if ext not in {'jpg', 'jpeg'} and ext != detected_type:
        raise ValueError('Разширението на файла не съответства на съдържанието.')

    if Image is not None:
        try:
            image = Image.open(uploaded_file.stream)
            image.verify()
        except Exception as exc:
            raise ValueError('Файлът не е валидно изображение.') from exc
        finally:
            uploaded_file.stream.seek(0)

    return ext


def save_service_invoice_image(upload):
    return save_uploaded_file(upload, 'service_invoices')


def append_service_invoice_marker(notes, invoice_path):
    notes = (notes or '').strip()
    if not invoice_path:
        return notes or None
    marker = f'[[service_invoice_image:{invoice_path}]]'
    return f'{notes}\n{marker}'.strip() if notes else marker


def extract_service_invoice_path(notes):
    if hasattr(notes, 'notes'):
        notes = notes.notes
    if not notes:
        return None
    match = re.search(r'\[\[service_invoice_image:(.*?)\]\]', notes)
    return match.group(1).strip() if match else None


def strip_service_invoice_marker(notes):
    if not notes:
        return None
    cleaned = re.sub(r'\n?\[\[service_invoice_image:.*?\]\]', '', notes).strip()
    return cleaned or None

CYR_TO_LAT = str.maketrans({
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh', 'з': 'z',
    'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p',
    'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sht', 'ъ': 'a', 'ь': '', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ж': 'Zh', 'З': 'Z',
    'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P',
    'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
    'Ш': 'Sh', 'Щ': 'Sht', 'Ъ': 'A', 'Ь': '', 'Ю': 'Yu', 'Я': 'Ya',
})

LAT_TO_CYR = {
    'shch': 'щ',
    'sht': 'щ',
    'zh': 'ж',
    'ch': 'ч',
    'sh': 'ш',
    'yu': 'ю',
    'ya': 'я',
    'ts': 'ц',
    'a': 'а',
    'b': 'б',
    'v': 'в',
    'g': 'г',
    'd': 'д',
    'e': 'е',
    'z': 'з',
    'i': 'и',
    'y': 'й',
    'k': 'к',
    'l': 'л',
    'm': 'м',
    'n': 'н',
    'o': 'о',
    'p': 'п',
    'r': 'р',
    's': 'с',
    't': 'т',
    'u': 'у',
    'f': 'ф',
    'h': 'х',
}


def transliterate_cyr_to_lat(value: str) -> str:
    return value.translate(CYR_TO_LAT)


def transliterate_lat_to_cyr(value: str) -> str:
    text = value.lower()
    result = []
    i = 0
    while i < len(text):
        matched = False
        for chunk_len in (4, 3, 2, 1):
            chunk = text[i:i + chunk_len]
            if chunk in LAT_TO_CYR:
                result.append(LAT_TO_CYR[chunk])
                i += chunk_len
                matched = True
                break
        if not matched:
            result.append(text[i])
            i += 1
    return ''.join(result)
def is_superuser():
    return getattr(g, 'user', None) is not None and g.user.role == ROLE_SUPERUSER


def user_has_linked_records(user_id):
    return any([
        Asset.query.filter_by(created_by_id=user_id).first(),
        TransferRequest.query.filter(
            or_(TransferRequest.requested_by_id == user_id, TransferRequest.approved_by_id == user_id)).first(),
        AssetHistory.query.filter_by(performed_by_id=user_id).first(),
        User.query.filter_by(manager_id=user_id).first(),
    ])


def allowed_image_filename(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_asset_image_upload(uploaded_file):
    return save_uploaded_file(uploaded_file, 'assets')


def asset_image_count(asset_id):
    return AssetImage.query.filter_by(asset_id=asset_id).count()


def normalize_asset_status_filter(value):
    return LOCATION_TYPE_TO_STATUS.get(STATUS_TO_LOCATION_TYPE.get((value or '').strip(), ''), (value or '').strip())


def build_asset_type_counts(base_query=None):
    asset_query = base_query or Asset.query
    type_counts = dict(
        asset_query
        .outerjoin(Location, Asset.current_location_id == Location.id)
        .with_entities(Location.type, func.count(Asset.id))
        .group_by(Location.type)
        .all()
    )
    return {
        'total': asset_query.order_by(None).count(),
        'warehouse': type_counts.get(LOC_WAREHOUSE, 0),
        'site': type_counts.get(LOC_SITE, 0),
        'service': type_counts.get(LOC_SERVICE, 0),
        'scrap': type_counts.get(LOC_SCRAP, 0),
    }


def add_asset_images(asset, uploaded_files):
    files = [f for f in uploaded_files if f and getattr(f, 'filename', '')]
    existing = asset_image_count(asset.id)
    if existing + len(files) > MAX_ASSET_IMAGES:
        raise ValueError('Може да качите максимум 3 снимки към един актив.')
    created = []
    for uploaded_file in files:
        file_path = save_asset_image_upload(uploaded_file)
        if file_path:
            created.append(AssetImage(asset_id=asset.id, file_path=file_path))
    for image in created:
        db.session.add(image)
    return created


def delete_upload_if_unreferenced(file_url, excluding_asset_image_ids=None, excluding_service_record_ids=None):
    if not file_url:
        return
    excluding_asset_image_ids = excluding_asset_image_ids or []
    excluding_service_record_ids = excluding_service_record_ids or []

    asset_image_query = AssetImage.query.filter_by(file_path=file_url)
    if excluding_asset_image_ids:
        asset_image_query = asset_image_query.filter(~AssetImage.id.in_(excluding_asset_image_ids))
    if asset_image_query.first():
        return

    service_records = AssetServiceRecord.query
    if excluding_service_record_ids:
        service_records = service_records.filter(~AssetServiceRecord.id.in_(excluding_service_record_ids))
    for record in service_records.with_entities(AssetServiceRecord.notes).all():
        if extract_service_invoice_path(record.notes) == file_url:
            return

    delete_uploaded_file(file_url)


def get_client_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def rate_limit_key(scope):
    user_id = getattr(getattr(g, 'user', None), 'id', None)
    return f'{scope}:{request.endpoint}:{get_client_ip()}:{user_id or "anon"}'


def is_rate_limited(scope, limit, window_seconds):
    now = time.time()
    bucket = RATE_LIMIT_BUCKETS[rate_limit_key(scope)]
    cutoff = now - window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.pop(0)
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def rate_limit_response(message):
    if request.endpoint == 'upload_asset_image' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': False, 'error': message}), 429
    if request.method == 'POST':
        flash(message, 'error')
        return redirect(request.referrer or url_for('dashboard'))
    abort(429)


def enforce_rate_limit(scope, limit, window_seconds, message):
    if is_rate_limited(scope, limit, window_seconds):
        app.logger.warning(
            'rate_limit_hit scope=%s endpoint=%s ip=%s user_id=%s',
            scope,
            request.endpoint,
            get_client_ip(),
            getattr(getattr(g, 'user', None), 'id', None),
        )
        return rate_limit_response(message)
    return None


def sensitive_rate_limited(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        blocked = enforce_rate_limit(
            'sensitive',
            SENSITIVE_RATE_LIMIT[0],
            SENSITIVE_RATE_LIMIT[1],
            'Твърде много чувствителни операции. Изчакайте малко и опитайте отново.',
        )
        if blocked is not None:
            return blocked
        return view(*args, **kwargs)

    return wrapped


def generate_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def csrf_error_response():
    if request.endpoint == 'upload_asset_image' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': False, 'error': 'Невалиден CSRF token.'}), 400
    abort(400)


def validate_csrf_token():
    session_token = session.get(CSRF_SESSION_KEY)
    request_token = request.form.get(CSRF_FORM_FIELD, '')
    if not request_token:
        for header_name in CSRF_HEADER_NAMES:
            request_token = request.headers.get(header_name, '')
            if request_token:
                break
    if not session_token or not request_token or not hmac.compare_digest(session_token, request_token):
        return False
    return True


@before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = db.session.get(User, user_id) if user_id else None


@before_request
def protect_against_csrf():
    if request.method not in UNSAFE_HTTP_METHODS:
        return None
    if request.endpoint == 'static':
        return None
    if not validate_csrf_token():
        return csrf_error_response()
    return None


@context_processor
def inject_helpers():
    return {
        'role_labels': ROLE_LABELS,
        'role_meta': ROLE_META,
        'location_meta': LOCATION_META,
        'location_minimal_types': LOCATION_MINIMAL_TYPES,
        'location_no_lead_types': LOCATION_NO_LEAD_TYPES,
        'status_meta': STATUS_META,
        'request_status_meta': REQUEST_STATUS_META,
        'action_labels': ACTION_LABELS,
        'now': datetime.utcnow,
        'field_roles': FIELD_ROLES,
        'multi_location_roles': MULTI_LOCATION_ROLES,
        'user_locations': user_locations,
        'role_label': lambda role: ROLE_LABELS.get(role, role),
        'can_view_users': can_view_users(g.user) if g.user else False,
        'can_create_asset': can_create_asset(g.user) if g.user else False,
        'can_create_location': can_manage_location(g.user) if g.user else False,
        'can_create_user': can_create_user(g.user) if g.user else False,
        'asset_display_status': asset_display_status,
    }


@context_processor
def inject_csrf_token():
    return {'csrf_token': generate_csrf_token}


@template_filter('role_label')
def render_role_label(role):
    return ROLE_LABELS.get(role, role)


@route('/')
def root():
    if getattr(g, 'user', None):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for('login'))
            if g.user.role not in roles:
                app.logger.warning(
                    'permission_denied user_id=%s role=%s endpoint=%s required_roles=%s',
                    g.user.id,
                    g.user.role,
                    request.endpoint,
                    ','.join(roles),
                )
                flash('Нямате права за тази операция.', 'error')
                return redirect(url_for('dashboard'))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def can_view_users(user):
    return bool(user and user.role == ROLE_SUPERUSER)


def can_create_user(user):
    return bool(user and any(can_create_user_role(user, role) for role in ROLE_META))


def user_scope_location_ids(user):
    if not user:
        return set()

    location_ids = set()
    assigned_location_id = getattr(user, 'assigned_location_id', None)
    if assigned_location_id:
        location_ids.add(assigned_location_id)

    for location in getattr(user, 'managed_locations', []) or []:
        if location and location.id:
            location_ids.add(location.id)

    if getattr(user, 'id', None):
        lead_location_ids = [
            row.id for row in Location.query.with_entities(Location.id).filter_by(technical_lead_id=user.id).all()
        ]
        location_ids.update(lead_location_ids)

    return location_ids


def user_in_scope(manager, target):
    if not manager or not target:
        return False
    if target.manager_id == manager.id:
        return True

    location_ids = user_scope_location_ids(manager)
    if not location_ids:
        return False
    if target.assigned_location_id in location_ids:
        return True

    for location in getattr(target, 'managed_locations', []) or []:
        if location and location.id in location_ids:
            return True
    return False


def asset_in_user_scope(user, asset):
    return bool(user and asset)


def can_view_user(current_user, target_user):
    if not current_user or not target_user:
        return False
    if target_user.is_active:
        return True
    return current_user.role == ROLE_SUPERUSER or current_user.id == target_user.id


def can_manage_user(current_user, target_user):
    if not current_user or not target_user:
        return False
    if current_user.role == ROLE_SUPERUSER:
        return True
    if current_user.role == ROLE_USER_PLUS:
        return target_user.role in FIELD_ROLES and target_user.manager_id == current_user.id
    return False


def can_create_user_role(current_user, role):
    if not current_user or role not in ROLE_META:
        return False
    if current_user.role == ROLE_SUPERUSER:
        return True
    if current_user.role == ROLE_USER_PLUS:
        return role in FIELD_ROLES
    return False


def can_change_user_role(current_user, target_user, new_role):
    if not current_user or not target_user or new_role not in ROLE_META:
        return False
    if current_user.role == ROLE_SUPERUSER:
        return True
    return can_manage_user(current_user, target_user) and new_role == target_user.role


def can_toggle_user(current_user, target_user):
    return bool(
        current_user
        and target_user
        and current_user.role == ROLE_SUPERUSER
        and current_user.id != target_user.id
    )


def can_delete_user(current_user, target_user):
    return can_toggle_user(current_user, target_user)


def can_view_asset(current_user, asset):
    return bool(current_user and asset)


def can_create_asset(current_user):
    return bool(current_user and current_user.role == ROLE_SUPERUSER)


def can_edit_asset(current_user, asset):
    if not current_user or not asset:
        return False
    if current_user.role == ROLE_SUPERUSER:
        return True
    if current_user.role == ROLE_USER_PLUS:
        location_ids = user_scope_location_ids(current_user)
        return bool(asset.current_location_id and asset.current_location_id in location_ids)
    return False


def can_edit_asset_notes_and_images(current_user, asset):
    if not current_user or not asset or not current_user.is_active:
        return False
    if current_user.role == ROLE_SUPERUSER:
        return True
    if not asset.current_location_id:
        return False
    return asset.current_location_id in get_user_assigned_location_ids(current_user)


def can_delete_asset(current_user, asset):
    return bool(current_user and asset and current_user.role == ROLE_SUPERUSER)


def can_upload_asset_image(current_user, asset=None):
    if not current_user:
        return False
    if asset is None:
        return current_user.role in {ROLE_SUPERUSER, ROLE_USER_PLUS}
    return can_edit_asset_notes_and_images(current_user, asset)


def can_view_location(current_user, location):
    return bool(current_user and location)


def can_manage_location(current_user, location=None):
    return bool(current_user and current_user.role == ROLE_SUPERUSER)


def can_view_request(current_user, transfer_request):
    if not current_user or not transfer_request:
        return False
    return True


def can_create_transfer_request(current_user, asset):
    return can_view_asset(current_user, asset)


def can_approve_request(current_user, transfer_request):
    return bool(
        current_user
        and transfer_request
        and current_user.role == ROLE_SUPERUSER
        and transfer_request.status == 'pending'
    )


def can_reject_request(current_user, transfer_request):
    return can_approve_request(current_user, transfer_request)


def can_direct_transfer(current_user, asset, to_location):
    if not current_user or not asset or not to_location:
        return False
    from_loc = asset.current_location
    if not from_loc:
        return False
    if asset.current_location_id == to_location.id:
        return False
    if current_user.role == ROLE_SUPERUSER:
        return True
    if current_user.role == ROLE_WAREHOUSE_WORKER:
        if from_loc.type != LOC_WAREHOUSE:
            return False
        location_ids = user_scope_location_ids(current_user)
        if not location_ids or from_loc.id not in location_ids:
            return False
        return to_location.type in {LOC_WAREHOUSE, LOC_SITE, LOC_SERVICE}
    return False


def can_move_asset(current_user, asset):
    return bool(current_user and can_view_asset(current_user, asset) and asset.current_location)


def can_view_service_record(current_user, record):
    return bool(record and can_view_asset(current_user, record.asset))


def can_add_service_record(current_user, asset):
    return can_view_asset(current_user, asset)


def can_edit_service_record(current_user, record):
    if not current_user or not record or not can_view_service_record(current_user, record):
        return False
    return current_user.role == ROLE_SUPERUSER or record.created_by_id == current_user.id


def can_delete_service_record(current_user, record):
    return bool(current_user and record and current_user.role == ROLE_SUPERUSER and can_view_service_record(current_user, record))


def visible_users_query(current_user, query):
    if not current_user:
        return query.filter(User.id == -1)
    if current_user.role == ROLE_SUPERUSER:
        return query
    if current_user.role == ROLE_USER_PLUS:
        location_ids = user_scope_location_ids(current_user)
        scope_filters = [User.manager_id == current_user.id]
        if location_ids:
            scope_filters.extend([
                User.assigned_location_id.in_(location_ids),
                User.managed_locations.any(Location.id.in_(location_ids)),
            ])
        return query.filter(or_(
            User.id == current_user.id,
            and_(User.role.in_(FIELD_ROLES), or_(*scope_filters)),
        ))
    return query.filter(User.id == current_user.id)


def apply_asset_scope(query, current_user):
    if not current_user:
        return query.filter(Asset.id == -1)
    return query


def apply_request_scope(query, current_user):
    if not current_user:
        return query.filter(TransferRequest.id == -1)
    return query


def assignable_locations_for_user(current_user):
    base_query = Location.query.filter(
        Location.type.in_([LOC_SITE, LOC_WAREHOUSE]),
        Location.is_active.is_(True),
    )
    if current_user and current_user.role == ROLE_SUPERUSER:
        return base_query.order_by(Location.name).all()
    location_ids = user_scope_location_ids(current_user)
    if not location_ids:
        return []
    return base_query.filter(Location.id.in_(location_ids)).order_by(Location.name).all()


def user_can_assign_locations(current_user, location_ids):
    location_ids = {int(location_id) for location_id in location_ids if location_id}
    if not location_ids:
        return True
    if current_user and current_user.role == ROLE_SUPERUSER:
        return True
    if current_user and current_user.role == ROLE_USER_PLUS:
        return location_ids.issubset(user_scope_location_ids(current_user))
    return False


def add_history(asset_id, action, details, performed_by_id=None):
    db.session.add(AssetHistory(asset_id=asset_id, action=action, details=details, performed_by_id=performed_by_id))


def get_user_assigned_location_ids(user):
    return user_scope_location_ids(user)


def normalize_user_primary_location(user):
    if not user:
        return

    if user.role in MULTI_LOCATION_ROLES:
        user.assigned_location_id = None
        return

    managed_ids = sorted(
        {
            location.id for location in getattr(user, 'managed_locations', []) or []
            if location and location.id and getattr(location, 'is_active', True)
        }
    )

    if user.assigned_location_id in managed_ids:
        return

    user.assigned_location_id = managed_ids[0] if managed_ids else None


def remove_location_from_user_profiles(location):
    if not location or location.id is None:
        return

    affected_users = {user for user in getattr(location, 'technicians', []) or [] if user}
    assigned_users = User.query.filter_by(assigned_location_id=location.id).all()
    affected_users.update(user for user in assigned_users if user)

    location.technicians = []

    for user in affected_users:
        if user.assigned_location_id == location.id:
            user.assigned_location_id = None
        normalize_user_primary_location(user)


def apply_user_location_assignments(user, *, assigned_location_id=None, team_location_ids=None, assigned_location_provided=True):
    team_location_ids = [int(location_id) for location_id in (team_location_ids or []) if location_id]

    if assigned_location_id and assigned_location_id not in team_location_ids:
        team_location_ids.insert(0, assigned_location_id)

    if assigned_location_provided:
        user.assigned_location_id = assigned_location_id if user.role not in MULTI_LOCATION_ROLES else None

    sync_user_location_team(user, team_location_ids)
    normalize_user_primary_location(user)


def asset_status_from_location(location):
    if not location:
        return STATUS_WAREHOUSE
    if location.type == LOC_SITE:
        return STATUS_SITE
    if location.type == LOC_SERVICE:
        return STATUS_SERVICE
    if location.type == LOC_SCRAP:
        return STATUS_SCRAP
    return STATUS_WAREHOUSE


def asset_condition_from_status(status):
    if status == STATUS_SERVICE:
        return 'За ремонт'
    if status == STATUS_SCRAP:
        return 'Бракуван'
    if status == 'Липсва':
        return 'Липсващ'
    if status == 'Откраднат':
        return 'Откраднат'
    return 'Работи'


def asset_display_status(asset):
    if not asset:
        return 'Без локация'
    if getattr(asset, 'current_location', None):
        return asset_status_from_location(asset.current_location)
    return 'Без локация'


def resolve_upload_fs_path(file_reference):
    if supabase_storage_enabled() or not file_reference:
        return None
    normalized = file_reference.strip()
    static_url_path = (app.static_url_path or '/static').rstrip('/') + '/'
    if normalized.startswith(static_url_path):
        normalized = normalized[len(static_url_path):]
        fs_path = os.path.normpath(os.path.join(app.static_folder or STATIC_ROOT, normalized.replace('/', os.sep)))
    elif normalized.startswith('/static/'):
        normalized = normalized[len('/static/'):]
        fs_path = os.path.normpath(os.path.join(app.static_folder or STATIC_ROOT, normalized.replace('/', os.sep)))
    elif normalized.startswith('/'):
        normalized = normalized[1:]
        fs_path = os.path.normpath(os.path.join(BASE_DIR, normalized.replace('/', os.sep)))
    else:
        fs_path = os.path.normpath(os.path.join(BASE_DIR, normalized.replace('/', os.sep)))

    uploads_root = os.path.normpath(os.path.abspath(configured_upload_folder()))
    fs_path = os.path.normpath(os.path.abspath(fs_path))
    if fs_path.startswith(uploads_root):
        return fs_path
    return None


def is_file_still_referenced(file_reference, *, excluding_asset_image_ids=None, excluding_service_record_ids=None):
    excluding_asset_image_ids = set(excluding_asset_image_ids or [])
    excluding_service_record_ids = {int(record_id) for record_id in (excluding_service_record_ids or [])}

    asset_image_query = AssetImage.query.filter_by(file_path=file_reference)
    if excluding_asset_image_ids:
        asset_image_query = asset_image_query.filter(~AssetImage.id.in_(excluding_asset_image_ids))
    if asset_image_query.first():
        return True

    service_records = AssetServiceRecord.query
    if excluding_service_record_ids:
        service_records = service_records.filter(~AssetServiceRecord.id.in_(excluding_service_record_ids))
    for record in service_records.with_entities(AssetServiceRecord.notes).all():
        if extract_service_invoice_path(record.notes) == file_reference:
            return True
    return False


def delete_upload_if_unreferenced(file_reference, *, excluding_asset_image_ids=None, excluding_service_record_ids=None):
    if not file_reference:
        return False
    if is_file_still_referenced(
        file_reference,
        excluding_asset_image_ids=excluding_asset_image_ids,
        excluding_service_record_ids=excluding_service_record_ids,
    ):
        return False
    if supabase_storage_enabled():
        delete_uploaded_file(file_reference)
        return True
    fs_path = resolve_upload_fs_path(file_reference)
    if not fs_path:
        return False
    if os.path.exists(fs_path):
        try:
            os.remove(fs_path)
            return True
        except OSError:
            app.logger.warning('upload_cleanup_failed path=%s', fs_path)
    return False


def asset_status_matches_location(status, location):
    if not location:
        return False
    location_status_map = {
        LOC_WAREHOUSE: STATUS_WAREHOUSE,
        LOC_SITE: STATUS_SITE,
        LOC_SERVICE: STATUS_SERVICE,
        LOC_SCRAP: STATUS_SCRAP,
    }
    expected = location_status_map.get(location.type)
    if status in {STATUS_WAREHOUSE, STATUS_SITE, STATUS_SERVICE, STATUS_SCRAP}:
        return status == expected
    return True


def clear_user_links(user_id):
    Asset.query.filter_by(created_by_id=user_id).update({'created_by_id': None}, synchronize_session=False)
    Asset.query.filter_by(responsible_user_id=user_id).update({'responsible_user_id': None}, synchronize_session=False)
    TransferRequest.query.filter(
        or_(TransferRequest.requested_by_id == user_id, TransferRequest.approved_by_id == user_id)
    ).delete(synchronize_session=False)
    AssetHistory.query.filter_by(performed_by_id=user_id).update({'performed_by_id': None}, synchronize_session=False)
    User.query.filter_by(manager_id=user_id).update({'manager_id': None}, synchronize_session=False)
    Location.query.filter_by(technical_lead_id=user_id).update({'technical_lead_id': None}, synchronize_session=False)


def clear_location_links(location_id):
    Asset.query.filter_by(current_location_id=location_id).update({'current_location_id': None}, synchronize_session=False)
    User.query.filter_by(assigned_location_id=location_id).update({'assigned_location_id': None}, synchronize_session=False)
    TransferRequest.query.filter(
        or_(TransferRequest.from_location_id == location_id, TransferRequest.to_location_id == location_id)
    ).delete(synchronize_session=False)


def sync_location_team(location, technician_ids):
    selected_ids = [int(t_id) for t_id in technician_ids if t_id]
    selected_users = User.query.filter(User.id.in_(selected_ids), User.is_active.is_(True)).all() if selected_ids else []
    current_users = list(location.technicians)
    current_ids = {user.id for user in current_users}
    selected_id_set = {user.id for user in selected_users}

    if location.id is None:
        db.session.flush()

    location.technicians = selected_users

    added_users = [user for user in selected_users if user.id not in current_ids]
    removed_users = [user for user in current_users if user.id not in selected_id_set]

    for user in added_users:
        if user.role not in MULTI_LOCATION_ROLES and not user.assigned_location_id:
            user.assigned_location_id = location.id

    for user in removed_users:
        if user.assigned_location_id == location.id:
            user.assigned_location_id = None

    for user in added_users + removed_users:
        normalize_user_primary_location(user)


def ensure_location_lead_in_team(location):
    if not location or not location.technical_lead_id:
        return
    lead = db.session.get(User, location.technical_lead_id)
    if not lead or not lead.is_active:
        return
    if lead not in location.technicians:
        location.technicians.append(lead)


def get_location_team(location):
    team_users = []
    seen_ids = set()

    manual_users = (
        list(getattr(location, 'technicians', []) or [])
        if location is not None
        else []
    )
    assigned_users = (
        User.query.filter_by(assigned_location_id=location.id, is_active=True).all()
        if location and location.id is not None
        else []
    )

    for user in manual_users + assigned_users:
        if not user or not user.is_active or user.id in seen_ids:
            continue
        team_users.append(user)
        seen_ids.add(user.id)

    return team_users


def selectable_location_team_users(location=None):
    selectable_users = User.query.filter(
        User.is_active.is_(True),
        User.role.in_(OPERATIONAL_TEAM_ROLES),
    ).order_by(User.full_name).all()
    users_by_id = {user.id: user for user in selectable_users}

    for user in get_location_team(location) if location else []:
        if user and user.id not in users_by_id:
            users_by_id[user.id] = user

    return sorted(users_by_id.values(), key=lambda user: user.full_name.lower())


def filter_location_team_ids(location, technician_ids):
    requested_ids = list(dict.fromkeys(int(t_id) for t_id in technician_ids if t_id))
    if not requested_ids:
        return []

    allowed_ids = {
        row.id for row in User.query.with_entities(User.id).filter(
            User.id.in_(requested_ids),
            User.is_active.is_(True),
            User.role.in_(OPERATIONAL_TEAM_ROLES),
        ).all()
    }
    existing_ids = {user.id for user in get_location_team(location)} if location else set()
    return [user_id for user_id in requested_ids if user_id in allowed_ids or user_id in existing_ids]


def filter_location_lead_id(location, lead_id):
    if not lead_id:
        return None
    lead = db.session.get(User, lead_id)
    if not lead or not lead.is_active:
        return None
    existing_lead_id = location.technical_lead_id if location else None
    if lead.role in {ROLE_USER_PLUS, ROLE_USER, ROLE_SUPERUSER} or lead.id == existing_lead_id:
        return lead.id
    return None


def user_locations(user):
    locations = []
    seen_ids = set()

    for location in getattr(user, 'managed_locations', []) or []:
        if location and location.id not in seen_ids and getattr(location, 'is_active', True):
            locations.append(location)
            seen_ids.add(location.id)

    assigned_location = getattr(user, 'assigned_location', None)
    if assigned_location and assigned_location.id not in seen_ids and getattr(assigned_location, 'is_active', True):
        locations.append(assigned_location)

    return sorted(locations, key=lambda location: location.name.lower())


def backfill_user_locations():
    users = (
        User.query
        .options(selectinload(User.assigned_location), selectinload(User.managed_locations))
        .order_by(User.id.asc())
        .all()
    )
    updated_users = 0

    for user in users:
        if user.role in MULTI_LOCATION_ROLES:
            continue

        locations = user_locations(user)
        if not locations:
            continue

        primary_location = locations[0]
        if user.assigned_location_id != primary_location.id:
            user.assigned_location_id = primary_location.id
            updated_users += 1

    if updated_users:
        db.session.commit()
    return updated_users


def sync_user_location_team(user, location_ids):
    selected_ids = [int(location_id) for location_id in location_ids if location_id]
    if user.id is None:
        db.session.flush()
    current_locations = Location.query.filter(Location.technicians.any(User.id == user.id)).all()
    next_ids = set(selected_ids)
    for location in current_locations:
        if location.id not in next_ids and user in location.technicians:
            location.technicians.remove(user)
    if next_ids:
        locations = Location.query.filter(Location.id.in_(next_ids), Location.is_active.is_(True)).all()
        for location in locations:
            if user not in location.technicians:
                location.technicians.append(user)

    normalize_user_primary_location(user)


def validate_phone_number(phone_number):
    if not phone_number:
        return True
    return bool(re.fullmatch(r'[\d+\-\s()]{6,20}', phone_number))


def parse_date_input(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def parse_service_date(value):
    parsed = parse_date_input(value)
    return parsed or date.today()


def parse_service_price(value):
    if value in (None, ''):
        return 0.0
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        raise ValueError('Невалидна цена. Въведете число.')


def validate_user_payload(form, creating=False, target=None):
    errors = []
    full_name = form.get('full_name', '').strip()
    email = form.get('email', '').strip().lower()
    phone_number = form.get('phone_number', '').strip()
    role_provided = 'role' in form
    assigned_location_provided = 'assigned_location_id' in form
    team_location_ids_provided = 'team_location_ids' in form
    role = form.get('role', '').strip() if role_provided else (target.role if target else '')
    password = form.get('password', '').strip()
    assigned_location_id = None
    team_location_ids = []

    if assigned_location_provided:
        try:
            if form.get('assigned_location_id'):
                assigned_location_id = int(form.get('assigned_location_id'))
        except (TypeError, ValueError):
            errors.append('Избраният обект е невалиден.')

    if team_location_ids_provided:
        try:
            team_location_ids = [int(location_id) for location_id in form.getlist('team_location_ids') if location_id]
        except (TypeError, ValueError):
            errors.append('Един или повече екипни обекти са невалидни.')

    if assigned_location_id and assigned_location_id not in team_location_ids:
        team_location_ids.insert(0, assigned_location_id)

    if not full_name or len(full_name) < 3:
        errors.append('Името и фамилията трябва да са поне 3 символа.')
    if len(full_name) > 120:
        errors.append('Името и фамилията не може да е по-дълго от 120 символа.')
    if not email or '@' not in email or email.startswith('@') or email.endswith('@'):
        errors.append('Въведи валиден имейл.')
    if len(email) > 120:
        errors.append('Имейлът не може да е по-дълъг от 120 символа.')
    if phone_number and not validate_phone_number(phone_number):
        errors.append('Телефонният номер е невалиден.')
    if creating and len(password) < 8:
        errors.append('Паролата трябва да е поне 8 символа.')
    if role and role not in ROLE_META:
        errors.append('Невалидна роля.')

    location_ids = []
    if assigned_location_id:
        location_ids.append(assigned_location_id)
    location_ids.extend(team_location_ids)
    location_ids = list(dict.fromkeys(location_ids))
    if location_ids:
        active_location_ids = {
            location.id for location in Location.query.filter(
                Location.id.in_(location_ids),
                Location.is_active.is_(True),
            ).all()
        }
        missing_ids = [location_id for location_id in location_ids if location_id not in active_location_ids]
        if missing_ids:
            errors.append('Избран е невалиден или неактивен обект.')

    if errors:
        for error in errors:
            flash(error, 'error')
        return None

    return {
        'full_name': full_name,
        'email': email,
        'phone_number': phone_number,
        'role': role,
        'password': password,
        'assigned_location_id': assigned_location_id,
        'assigned_location_provided': assigned_location_provided,
        'team_location_ids': list(dict.fromkeys(team_location_ids)),
        'team_location_ids_provided': team_location_ids_provided,
        'role_provided': role_provided,
    }


def user_can_direct_transfer(user, asset, to_location):
    return can_direct_transfer(user, asset, to_location)


def update_asset_status(asset, target_location):
    asset.current_location_id = target_location.id
    if target_location.type == LOC_WAREHOUSE:
        asset.status = STATUS_WAREHOUSE
    elif target_location.type == LOC_SITE:
        asset.status = STATUS_SITE
    elif target_location.type == LOC_SERVICE:
        asset.status = STATUS_SERVICE
    elif target_location.type == LOC_SCRAP:
        asset.status = STATUS_SCRAP
    asset.condition = asset_condition_from_status(asset.status)
    asset.last_moved_at = datetime.utcnow()


def init_database():
    """Create an empty database schema without demo data."""
    db.create_all()
    ensure_database_compatibility()
    normalize_legacy_roles()
    ensure_database_indexes()


def ensure_database_compatibility():
    """Apply small schema fixes for older SQLite databases."""
    if db.engine.dialect.name != 'sqlite':
        return

    with db.engine.begin() as connection:
        user_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info('user')").fetchall()
        }
        if 'phone_number' not in user_columns:
            connection.exec_driver_sql("ALTER TABLE user ADD COLUMN phone_number VARCHAR(20)")

        location_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info('location')").fetchall()
        }
        location_column_sql = {
            'city': "ALTER TABLE location ADD COLUMN city VARCHAR(100)",
            'address': "ALTER TABLE location ADD COLUMN address VARCHAR(255)",
            'gps_location': "ALTER TABLE location ADD COLUMN gps_location VARCHAR(100)",
            'courier_locations': "ALTER TABLE location ADD COLUMN courier_locations VARCHAR(255)",
            'technical_lead_id': "ALTER TABLE location ADD COLUMN technical_lead_id INTEGER",
        }
        for column_name, statement in location_column_sql.items():
            if column_name not in location_columns:
                connection.exec_driver_sql(statement)

        asset_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info('asset')").fetchall()
        }
        asset_column_sql = {
            'asset_type': "ALTER TABLE asset ADD COLUMN asset_type VARCHAR(30) DEFAULT 'Машина'",
            'alias_name': "ALTER TABLE asset ADD COLUMN alias_name VARCHAR(120)",
            'purchase_date': "ALTER TABLE asset ADD COLUMN purchase_date DATE",
            'supplier_company': "ALTER TABLE asset ADD COLUMN supplier_company VARCHAR(150)",
            'warranty': "ALTER TABLE asset ADD COLUMN warranty VARCHAR(150)",
            'condition': "ALTER TABLE asset ADD COLUMN condition VARCHAR(50) DEFAULT 'Работи'",
            'responsible_user_id': "ALTER TABLE asset ADD COLUMN responsible_user_id INTEGER",
            'last_moved_at': "ALTER TABLE asset ADD COLUMN last_moved_at DATETIME",
        }
        for column_name, statement in asset_column_sql.items():
            if column_name not in asset_columns:
                connection.exec_driver_sql(statement)

        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS asset_image (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(asset_id) REFERENCES asset (id) ON DELETE CASCADE
            )
            """
        )


def ensure_database_indexes():
    # SQLAlchemy/Alembic creates declared indexes for PostgreSQL. These raw
    # SQLite maintenance statements are kept only for old local SQLite files.
    if db.engine.dialect.name != 'sqlite':
        return

    index_statements = [
        'CREATE INDEX IF NOT EXISTS ix_user_role ON user (role)',
        'CREATE INDEX IF NOT EXISTS ix_user_assigned_location_id ON user (assigned_location_id)',
        'CREATE INDEX IF NOT EXISTS ix_user_manager_id ON user (manager_id)',
        'CREATE INDEX IF NOT EXISTS ix_location_type ON location (type)',
        'CREATE INDEX IF NOT EXISTS ix_asset_status ON asset (status)',
        'CREATE INDEX IF NOT EXISTS ix_asset_asset_type ON asset (asset_type)',
        'CREATE INDEX IF NOT EXISTS ix_asset_condition ON asset (condition)',
        'CREATE INDEX IF NOT EXISTS ix_asset_responsible_user_id ON asset (responsible_user_id)',
        'CREATE INDEX IF NOT EXISTS ix_asset_current_location_id ON asset (current_location_id)',
        'CREATE INDEX IF NOT EXISTS ix_asset_last_moved_at ON asset (last_moved_at)',
        'CREATE INDEX IF NOT EXISTS ix_asset_created_at ON asset (created_at)',
        'CREATE INDEX IF NOT EXISTS ix_transfer_request_status ON transfer_request (status)',
        'CREATE INDEX IF NOT EXISTS ix_transfer_request_requested_by_id ON transfer_request (requested_by_id)',
        'CREATE INDEX IF NOT EXISTS ix_transfer_request_created_at ON transfer_request (created_at)',
        'CREATE INDEX IF NOT EXISTS ix_asset_history_asset_id ON asset_history (asset_id)',
        'CREATE INDEX IF NOT EXISTS ix_asset_history_created_at ON asset_history (created_at)',
        'CREATE INDEX IF NOT EXISTS ix_asset_service_record_asset_id ON asset_service_record (asset_id)',
        'CREATE INDEX IF NOT EXISTS ix_asset_service_record_service_date ON asset_service_record (service_date)',
        'CREATE INDEX IF NOT EXISTS ix_asset_image_asset_id ON asset_image (asset_id)',
        'CREATE INDEX IF NOT EXISTS ix_asset_image_created_at ON asset_image (created_at)',
    ]
    with db.engine.begin() as connection:
        for statement in index_statements:
            connection.exec_driver_sql(statement)


def normalize_legacy_roles():
    """Map any legacy or unsupported roles onto the current role set."""
    valid_roles = list(ROLE_META.keys())
    legacy_users = User.query.filter(~User.role.in_(valid_roles)).all()
    if not legacy_users:
        return 0

    for user in legacy_users:
        user.role = ROLE_WAREHOUSE_WORKER

    db.session.commit()
    return len(legacy_users)


@route('/init-db', methods=['POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
@sensitive_rate_limited
def init_db():
    if not is_superuser():
        abort(403)
    init_database()
    flash('Базата данни е инициализирана без примерни данни.', 'success')
    return redirect(url_for('dashboard'))


@route('/', methods=['GET'])
def home():
    if g.user:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        blocked = enforce_rate_limit(
            'login',
            LOGIN_RATE_LIMIT[0],
            LOGIN_RATE_LIMIT[1],
            'Твърде много опити за вход. Изчакайте няколко минути и опитайте отново.',
        )
        if blocked is not None:
            return blocked
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            session.clear()
            session.permanent = True
            session['user_id'] = user.id
            app.logger.info('login_success user_id=%s email=%s ip=%s', user.id, user.email, get_client_ip())
            next_url = request.args.get('next', '')
            if next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect(url_for('dashboard'))
        app.logger.warning('login_failure email=%s ip=%s', email, get_client_ip())
        flash('Грешен имейл, парола или неактивен потребител.', 'error')
    return render_template('login.html')


@route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'full_name' in request.form:
            payload = validate_user_payload(request.form, creating=False, target=g.user)
            if payload is None:
                return redirect(url_for('profile'))
            if payload['role'] != g.user.role:
                flash('Не можете да променяте ролята на собствения си профил.', 'error')
                return redirect(url_for('profile'))
            g.user.full_name = payload['full_name']
            g.user.email = payload['email']
            g.user.phone_number = payload['phone_number']
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('Вече има потребител с този имейл.', 'error')
                return redirect(url_for('profile'))
            flash('Профилът е обновен.', 'success')
            return redirect(url_for('profile'))

        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        password_change_requested = any([current_password, new_password, confirm_password])

        if password_change_requested:
            if not current_password:
                flash('Въведи текущата си парола, за да смениш паролата.', 'error')
                return redirect(url_for('profile'))
            if not g.user.check_password(current_password):
                flash('Текущата парола е грешна.', 'error')
                return redirect(url_for('profile'))
            if len(new_password) < 8:
                flash('Новата парола трябва да е поне 8 символа.', 'error')
                return redirect(url_for('profile'))
            if new_password != confirm_password:
                flash('Новата парола и потвърждението не съвпадат.', 'error')
                return redirect(url_for('profile'))
            g.user.set_password(new_password)
            db.session.commit()
            flash('Паролата е обновена.', 'success')
            return redirect(url_for('profile'))

        if 'phone_number' in request.form:
            phone_number = request.form.get('phone_number', '').strip()
            if phone_number and not validate_phone_number(phone_number):
                flash('Телефонният номер е невалиден.', 'error')
                return redirect(url_for('profile'))
            g.user.phone_number = phone_number
            db.session.commit()
            flash('Телефонният номер е обновен.', 'success')
            return redirect(url_for('profile'))

        flash('Няма данни за запис.', 'error')
        return redirect(url_for('profile'))
    locations = Location.query.filter(Location.type.in_([LOC_SITE, LOC_WAREHOUSE]), Location.is_active.is_(True)).order_by(Location.name).all()
    all_locations = Location.query.filter(Location.is_active.is_(True)).order_by(Location.name).all()
    return render_template(
        'profile.html',
        user=g.user,
        is_self=True,
        can_manage=False,
        can_edit_user=True,
        can_toggle_user=False,
        can_delete_user=False,
        locations=locations,
        all_locations=all_locations,
    )


@route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    can_change_own_assignments = g.user.role == ROLE_SUPERUSER
    if request.method == 'POST':
        payload = validate_user_payload(request.form, creating=False, target=g.user)
        if payload is None:
            return redirect(url_for('profile_edit'))
        if payload['role'] != g.user.role:
            flash('Не можете да променяте ролята на собствения си профил.', 'error')
            return redirect(url_for('profile_edit'))

        g.user.full_name = payload['full_name']
        g.user.email = payload['email']
        g.user.phone_number = payload['phone_number']
        try:
            if can_change_own_assignments and (
                payload['team_location_ids_provided'] or payload['assigned_location_provided']
            ):
                requested_location_ids = []
                if payload['assigned_location_id']:
                    requested_location_ids.append(payload['assigned_location_id'])
                requested_location_ids.extend(payload['team_location_ids'])
                if not user_can_assign_locations(g.user, requested_location_ids):
                    flash('Нямате право да назначавате потребител към избраните обекти.', 'error')
                    return redirect(url_for('profile_edit'))
                apply_user_location_assignments(
                    g.user,
                    assigned_location_id=payload['assigned_location_id'],
                    team_location_ids=payload['team_location_ids'],
                    assigned_location_provided=payload['assigned_location_provided'],
                )
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Вече има потребител с този имейл.', 'error')
            return redirect(url_for('profile_edit'))

        flash('Профилът е обновен.', 'success')
        return redirect(url_for('profile'))

    locations = Location.query.filter(Location.type.in_([LOC_SITE, LOC_WAREHOUSE]), Location.is_active.is_(True)).order_by(Location.name).all()
    all_locations = Location.query.filter(Location.is_active.is_(True)).order_by(Location.name).all()
    return render_template(
        'profile_edit.html',
        user=g.user,
        locations=locations,
        all_locations=all_locations,
        can_change_user_assignments=can_change_own_assignments,
    )


@route('/users/<int:user_id>/profile')
@login_required
def user_profile(user_id):
    target = (
        User.query
        .options(joinedload(User.assigned_location), joinedload(User.managed_locations))
        .get_or_404(user_id)
    )
    if not can_view_user(g.user, target):
        abort(403)
    if not target.is_active and not is_superuser() and target.id != g.user.id:
        abort(404)
    return render_template(
        'profile.html',
        user=target,
        is_self=target.id == g.user.id,
        can_manage=can_manage_user(g.user, target),
        can_edit_user=can_manage_user(g.user, target),
        can_toggle_user=can_toggle_user(g.user, target),
        can_delete_user=can_delete_user(g.user, target),
        show_users_back_link=g.user.role in {ROLE_SUPERUSER, ROLE_USER_PLUS},
    )


@route('/dashboard')
@login_required
def dashboard():
    asset_query = Asset.query
    request_query = apply_request_scope(TransferRequest.query, g.user)
    asset_counts = build_asset_type_counts(asset_query)
    stats = {
        'assets_total': asset_counts['total'],
        'warehouse_total': asset_counts['warehouse'],
        'site_total': asset_counts['site'],
        'service_total': asset_counts['service'],
        'scrap_total': asset_counts['scrap'],
        'pending_requests': request_query.filter_by(status='pending').count(),
    }
    recent_history = (
        AssetHistory.query
        .options(joinedload(AssetHistory.asset), joinedload(AssetHistory.performed_by))
        .order_by(AssetHistory.created_at.desc())
        .limit(10)
        .all()
    )
    pending_requests = (
        request_query
        .options(joinedload(TransferRequest.asset), joinedload(TransferRequest.from_location),
                 joinedload(TransferRequest.to_location))
        .filter_by(status='pending')
        .order_by(TransferRequest.created_at.desc())
        .limit(5)
        .all()
    )
    service_assets = (
        asset_query
        .join(Location, Asset.current_location_id == Location.id)
        .filter(Location.type == LOC_SERVICE)
        .order_by(Asset.created_at.desc())
        .limit(5)
        .all()
    )
    recent_assets = (
        asset_query
        .options(joinedload(Asset.current_location))
        .order_by(Asset.created_at.desc())
        .limit(6)
        .all()
    )
    location_counts = (
        db.session.query(Location, func.count(Asset.id).label('asset_count'))
        .join(Asset, Asset.current_location_id == Location.id)
        .group_by(Location.id)
        .order_by(Location.type, Location.name)
        .all()
    )
    return render_template(
        'dashboard.html',
        stats=stats,
        recent_history=recent_history,
        location_counts=location_counts,
        pending_requests=pending_requests,
        service_assets=service_assets,
        recent_assets=recent_assets,
        dashboard_locations=user_locations(g.user),
    )


@route('/assets')
@login_required
def assets():
    q = request.args.get('q', '').strip()
    status = normalize_asset_status_filter(request.args.get('status', '').strip())
    location_id = request.args.get('location', type=int) or request.args.get('location_id', type=int)
    category = request.args.get('category', '').strip()
    asset_type = request.args.get('asset_type', '').strip()
    condition = request.args.get('condition', '').strip()
    responsible_user_id = request.args.get('responsible_user_id', type=int)
    sort = request.args.get('sort', 'inventory').strip()
    direction = request.args.get('direction', 'asc').lower().strip()
    if direction not in ('asc', 'desc'):
        direction = 'asc'
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    query = Asset.query.options(joinedload(Asset.current_location), joinedload(Asset.created_by),
                                joinedload(Asset.responsible_user))
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            Asset.inventory_number.ilike(like),
            Asset.name.ilike(like),
            Asset.alias_name.ilike(like),
            Asset.brand.ilike(like),
            Asset.model.ilike(like),
            Asset.serial_number.ilike(like),
            Asset.company_name.ilike(like),
            Asset.supplier_company.ilike(like),
            Asset.invoice_number.ilike(like),
            Asset.notes.ilike(like),
            Asset.created_by.has(User.full_name.ilike(like)),
            Asset.responsible_user.has(User.full_name.ilike(like)),
            Asset.current_location.has(or_(
                Location.name.ilike(like),
                Location.city.ilike(like),
                Location.address.ilike(like),
            )),
        ))
    status_location_type = STATUS_TO_LOCATION_TYPE.get(status)
    if status_location_type:
        query = query.join(Location, Asset.current_location_id == Location.id).filter(Location.type == status_location_type)
    if location_id:
        query = query.filter_by(current_location_id=location_id)
    if category:
        query = query.filter(Asset.category == category)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if condition:
        query = query.filter_by(condition=condition)
    if responsible_user_id:
        query = query.filter_by(responsible_user_id=responsible_user_id)

    inventory_order = [cast(Asset.inventory_number, Integer), Asset.inventory_number]
    sort_map = {
        'inventory': inventory_order,
        'type': [Asset.asset_type],
        'brand': [Asset.brand],
        'model': [Asset.model],
        'serial': [Asset.serial_number],
        'purchase_date': [Asset.purchase_date],
        'created_at': [Asset.created_at],
    }
    columns = sort_map.get(sort, inventory_order)
    order_by = tuple(col.desc() if direction == 'desc' else col.asc() for col in columns)
    pagination = query.order_by(*order_by).paginate(page=page, per_page=15, error_out=False)
    locations = Location.query.order_by(Location.name).all()
    categories = [
        row[0] for row in db.session.query(Asset.category)
        .filter(Asset.category.isnot(None), Asset.category != '')
        .distinct()
        .order_by(Asset.category)
        .all()
    ]
    asset_types = [
        row[0] for row in db.session.query(Asset.asset_type)
        .filter(Asset.asset_type.isnot(None), Asset.asset_type != '')
        .distinct()
        .order_by(Asset.asset_type)
        .all()
    ]
    responsible_users = User.query.filter(User.is_active.is_(True)).order_by(User.full_name).all()
    asset_summary = build_asset_type_counts()

    def page_url(page_number):
        args = request.args.to_dict()
        args['page'] = page_number
        return url_for('assets', **args)

    filters = {
        'q': q,
        'status': status,
        'location_id': location_id,
        'condition': condition,
        'responsible_user_id': responsible_user_id,
        'sort': sort,
        'direction': direction,
    }
    return render_template('assets.html', items=pagination.items, pagination=pagination, page_url=page_url,
                           filters=filters, locations=locations, categories=categories, asset_types=asset_types,
                           responsible_users=responsible_users, asset_summary=asset_summary,
                           can_create_asset=can_create_asset(g.user))


@route('/assets/new', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
def asset_new():
    if request.method == 'POST':
        inventory_number = request.form.get('inventory_number', '').strip()
        type_name = request.form.get('name', '').strip()
        also_known_as = request.form.get('alias_name', '').strip()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        invoice_number = request.form.get('invoice_number', '').strip()
        supplier_company = request.form.get('supplier_company', '').strip()
        warranty = request.form.get('warranty', '').strip()
        purchase_date = parse_date_input(request.form.get('purchase_date', '').strip())
        notes = request.form.get('notes', '').strip()
        current_location_id = request.form.get('current_location_id', type=int)
        responsible_user_id = request.form.get('responsible_user_id', type=int)

        if not inventory_number:
            flash('Инвентарният № е задължителен.', 'error')
            return redirect(url_for('asset_new'))
        if not type_name:
            flash('Тип / Име е задължително.', 'error')
            return redirect(url_for('asset_new'))
        if purchase_date and purchase_date > datetime.utcnow().date():
            flash('Дата на закупуване не може да бъде в бъдещето.', 'error')
            return redirect(url_for('asset_new'))

        location = db.session.get(Location, current_location_id) if current_location_id else None
        if location and not location.is_active:
            flash('Изберете валидна локация.', 'error')
            return redirect(url_for('asset_new'))

        asset = Asset(
            inventory_number=inventory_number,
            name=type_name,
            category=type_name,
            brand=brand,
            model=model,
            serial_number=serial_number or None,
            alias_name=also_known_as or None,
            invoice_number=invoice_number or None,
            company_name=supplier_company or None,
            supplier_company=supplier_company or None,
            warranty=warranty or None,
            purchase_date=purchase_date,
            notes=notes or None,
            current_location_id=location.id if location else None,
            responsible_user_id=responsible_user_id,
            created_by_id=g.user.id,
        )
        if location:
            update_asset_status(asset, location)
        db.session.add(asset)
        try:
            db.session.flush()
            add_asset_images(asset, request.files.getlist('images'))
            add_history(asset.id, 'asset_created', f'Активът е създаден от {g.user.full_name}.', g.user.id)
            db.session.commit()
            flash('Активът е добавен успешно.', 'success')
            return redirect(url_for('assets'))
        except IntegrityError as exc:
            db.session.rollback()
            error_text = str(exc.orig).lower() if getattr(exc, 'orig', None) else str(exc).lower()
            if 'inventory_number' in error_text or 'unique constraint failed: asset.inventory_number' in error_text:
                flash('Грешка: Инвентарен номер вече съществува.', 'error')
            else:
                flash('Грешка при запазване на актива.', 'error')
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'error')

    locations = Location.query.filter(Location.is_active.is_(True)).order_by(Location.type, Location.name).all()
    return render_template('asset_form.html', locations=locations)


@route('/assets/<int:asset_id>')
@login_required
def asset_detail(asset_id):
    asset = Asset.query.options(joinedload(Asset.current_location), joinedload(Asset.responsible_user),
                                 joinedload(Asset.created_by), selectinload(Asset.images)).get_or_404(asset_id)
    if not can_view_asset(g.user, asset):
        abort(403)
    history_page = request.args.get('history_page', 1, type=int)
    history_pagination = (
        AssetHistory.query
        .options(joinedload(AssetHistory.performed_by))
        .filter_by(asset_id=asset_id)
        .order_by(AssetHistory.created_at.desc())
        .paginate(page=history_page, per_page=10, error_out=False)
    )
    history = history_pagination.items
    service_records = (
        AssetServiceRecord.query
        .options(joinedload(AssetServiceRecord.created_by))
        .filter_by(asset_id=asset_id)
        .order_by(AssetServiceRecord.service_date.desc())
        .all()
    )
    locations = Location.query.filter(Location.id != asset.current_location_id, Location.is_active.is_(True)).order_by(
        Location.type, Location.name).all()
    can_direct = {loc.id: can_direct_transfer(g.user, asset, loc) for loc in locations}
    pending_requests = (
        TransferRequest.query
        .options(joinedload(TransferRequest.to_location), joinedload(TransferRequest.requested_by))
        .filter_by(asset_id=asset_id, status='pending')
        .order_by(TransferRequest.created_at.desc())
        .all()
    )
    service_permissions = {
        record.id: {
            'edit': can_edit_service_record(g.user, record),
            'delete': can_delete_service_record(g.user, record),
        }
        for record in service_records
    }
    return render_template('asset_detail.html', asset=asset, history=history,
                           history_pagination=history_pagination, service_records=service_records,
                           locations=locations, can_direct=can_direct, pending_requests=pending_requests,
                           can_edit_asset=can_edit_asset(g.user, asset),
                           can_edit_asset_notes_and_images=can_edit_asset_notes_and_images(g.user, asset),
                           can_delete_asset=can_delete_asset(g.user, asset),
                           can_move_asset=can_move_asset(g.user, asset),
                           can_upload_asset_image=can_upload_asset_image(g.user, asset),
                           can_add_service_record=can_add_service_record(g.user, asset),
                           service_permissions=service_permissions)


@route('/assets/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
def asset_edit(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    can_full_edit = can_edit_asset(g.user, asset)
    can_notes_images_edit = can_edit_asset_notes_and_images(g.user, asset)
    if not can_notes_images_edit:
        flash('Нямате право да редактирате този актив.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    if request.method == 'POST':
        original_notes = asset.notes or ''
        original_fields = None
        location = asset.current_location

        if can_full_edit:
            original_fields = {
                'inventory_number': asset.inventory_number,
                'name': asset.name,
                'alias_name': asset.alias_name or '',
                'brand': asset.brand,
                'model': asset.model,
                'serial_number': asset.serial_number or '',
                'invoice_number': asset.invoice_number or '',
                'supplier_company': asset.supplier_company or asset.company_name or '',
                'warranty': asset.warranty or '',
                'purchase_date': asset.purchase_date.isoformat() if asset.purchase_date else '',
                'notes': original_notes,
            }
            current_location_id = request.form.get('current_location_id', type=int)
            if g.user.role == ROLE_SUPERUSER:
                location = db.session.get(Location, current_location_id) if current_location_id else None
            asset.inventory_number = request.form.get('inventory_number', '').strip()
            asset.name = request.form.get('name', '').strip()
            asset.category = asset.name
            asset.alias_name = request.form.get('alias_name', '').strip() or None
            asset.brand = request.form.get('brand', '').strip()
            asset.model = request.form.get('model', '').strip()
            asset.serial_number = request.form.get('serial_number', '').strip() or None
            asset.invoice_number = request.form.get('invoice_number', '').strip() or None
            asset.supplier_company = request.form.get('supplier_company', '').strip() or None
            asset.company_name = asset.supplier_company
            asset.warranty = request.form.get('warranty', '').strip() or None
            asset.purchase_date = parse_date_input(request.form.get('purchase_date', '').strip())
            if g.user.role == ROLE_SUPERUSER:
                asset.current_location_id = location.id if location else None
            if not asset.inventory_number:
                flash('Инвентарният № е задължителен.', 'error')
                return redirect(url_for('asset_edit', asset_id=asset.id))
            if not asset.name:
                flash('Тип / Име е задължително.', 'error')
                return redirect(url_for('asset_edit', asset_id=asset.id))
            if asset.purchase_date and asset.purchase_date > datetime.utcnow().date():
                flash('Дата на закупуване не може да бъде в бъдещето.', 'error')
                return redirect(url_for('asset_edit', asset_id=asset.id))

            if g.user.role == ROLE_SUPERUSER and location and not location.is_active:
                flash('Изберете валидна локация.', 'error')
                return redirect(url_for('asset_edit', asset_id=asset.id))
            if location and g.user.role == ROLE_SUPERUSER:
                update_asset_status(asset, location)

        asset.notes = request.form.get('notes', '').strip() or None

        remove_image_ids = {int(image_id) for image_id in request.form.getlist('remove_image_ids') if image_id}
        if remove_image_ids:
            images_to_remove = AssetImage.query.filter(AssetImage.asset_id == asset.id, AssetImage.id.in_(remove_image_ids)).all()
            for image in images_to_remove:
                asset.images.remove(image)
                delete_upload_if_unreferenced(image.file_path, excluding_asset_image_ids=[image.id])

        try:
            if request.files.getlist('images') and not can_upload_asset_image(g.user, asset):
                raise ValueError('Нямате право да качвате снимки към този актив.')
            add_asset_images(asset, request.files.getlist('images'))
            if can_full_edit and original_fields is not None:
                changed = [field for field, value in original_fields.items() if value != (getattr(asset, field) or '')]
                if changed:
                    add_history(asset.id, 'asset_updated', f'Променени полета: {", ".join(changed)}.', g.user.id)
            else:
                changes = []
                if original_notes != (asset.notes or ''):
                    changes.append('notes')
                if request.files.getlist('images') or remove_image_ids:
                    changes.append('images')
                if changes:
                    add_history(asset.id, 'asset_updated', f'Променени полета: {", ".join(changes)}.', g.user.id)
            db.session.commit()
            flash('Промените са записани.', 'success')
            return redirect(url_for('asset_detail', asset_id=asset.id))
        except IntegrityError as exc:
            db.session.rollback()
            error_text = str(exc.orig).lower() if getattr(exc, 'orig', None) else str(exc).lower()
            if 'inventory_number' in error_text or 'unique constraint failed: asset.inventory_number' in error_text:
                flash('Грешка: Инвентарен номер вече съществува.', 'error')
            else:
                flash('Грешка при запазване на актива.', 'error')
            return redirect(url_for('asset_edit', asset_id=asset.id))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
            return redirect(url_for('asset_edit', asset_id=asset.id))
    locations = Location.query.filter(Location.is_active.is_(True)).order_by(Location.type, Location.name).all()
    return render_template(
        'asset_edit.html',
        asset=asset,
        limited=(g.user.role == ROLE_USER_PLUS),
        notes_images_only=not can_full_edit,
        locations=locations,
        can_upload_asset_image=can_upload_asset_image(g.user, asset),
        can_change_asset_location=g.user.role == ROLE_SUPERUSER,
    )


@route('/assets/<int:asset_id>/service', methods=['POST'])
@login_required
def asset_service_add(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if not can_add_service_record(g.user, asset):
        flash('Нямате право да добавяте сервизен запис към този актив.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    problem = request.form.get('problem', '').strip()
    action_taken = request.form.get('action_taken', '').strip()
    service_provider = request.form.get('service_provider', '').strip()
    price = request.form.get('price', '').strip()
    notes = request.form.get('notes', '').strip()
    attachment_url = request.form.get('attachment_url', '').strip()
    service_file = request.files.get('attachment_file')

    if not problem or not action_taken:
        flash('Попълни проблем и предприето действие.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))

    if service_file and service_file.filename:
        try:
            attachment_url = save_asset_image_upload(service_file)
        except ValueError as exc:
            flash(str(exc), 'error')
            return redirect(url_for('asset_detail', asset_id=asset.id))

    record = AssetServiceRecord(
        asset_id=asset.id,
        problem=problem,
        action_taken=action_taken,
        service_provider=service_provider or None,
        price=price or None,
        notes=notes or None,
        attachment_url=attachment_url or None,
        created_by_id=g.user.id,
    )
    db.session.add(record)
    add_history(asset.id, 'service_added', f'Добавен сервизен запис от {g.user.full_name}.', g.user.id)
    db.session.commit()
    flash('Сервизният запис е добавен.', 'success')
    return redirect(url_for('asset_detail', asset_id=asset.id))


@route('/transfer/<int:asset_id>', methods=['POST'])
@login_required
def transfer_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if not can_move_asset(g.user, asset):
        flash('Нямате право да стартирате преместване за този актив.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    to_location_id = request.form.get('to_location_id', type=int)
    to_location = db.session.get(Location, to_location_id) if to_location_id else None
    reason = request.form.get('reason', '').strip()

    if not to_location or not to_location.is_active:
        flash('Изберете валидна локация.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))

    if not asset.current_location:
        flash('Машината няма текуща локация и трябва първо да бъде коригирана от Администратор.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))

    if asset.current_location_id == to_location.id:
        flash('Машината вече е на тази локация.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))

    if asset.current_location.type == LOC_SCRAP and g.user.role != ROLE_SUPERUSER:
        flash('Бракувана машина може да се връща само от Администратор.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))

    if asset.current_location.type == LOC_SCRAP and g.user.role == ROLE_SUPERUSER and to_location.type != LOC_SCRAP:
        old_location_id = asset.current_location_id
        old_name = asset.current_location.name
        update_asset_status(asset, to_location)
        req = TransferRequest(
            asset_id=asset.id,
            from_location_id=old_location_id,
            to_location_id=to_location.id,
            request_type='return',
            reason=reason,
            status='approved',
            requested_by_id=g.user.id,
            approved_by_id=g.user.id,
            processed_at=datetime.utcnow(),
        )
        db.session.add(req)
        add_history(
            asset.id,
            'asset_returned_from_scrap',
            f'Върната от брак от {old_name} към {to_location.name} от {g.user.full_name}.',
            g.user.id,
        )
        db.session.commit()
        flash('Машината е върната от брак успешно.', 'success')
        return redirect(url_for('asset_detail', asset_id=asset.id))

    if can_direct_transfer(g.user, asset, to_location):
        old_location_id = asset.current_location_id
        old_name = asset.current_location.name
        update_asset_status(asset, to_location)
        req = TransferRequest(asset_id=asset.id, from_location_id=old_location_id, to_location_id=to_location.id,
                              request_type='transfer', reason=reason, status='approved', requested_by_id=g.user.id,
                              approved_by_id=g.user.id, processed_at=datetime.utcnow())
        db.session.add(req)
        add_history(asset.id, 'asset_transferred',
                    f'Преместена от {old_name} към {to_location.name} от {g.user.full_name}.', g.user.id)
        db.session.commit()
        flash('Машината е преместена успешно.', 'success')
    else:
        if not can_create_transfer_request(g.user, asset):
            flash('Нямате право да създадете заявка за този актив.', 'error')
            return redirect(url_for('asset_detail', asset_id=asset.id))
        req_type = 'scrap' if to_location.type == LOC_SCRAP else 'transfer'
        req = TransferRequest(asset_id=asset.id, from_location_id=asset.current_location_id,
                              to_location_id=to_location.id,
                              request_type=req_type, reason=reason, status='pending', requested_by_id=g.user.id)
        db.session.add(req)
        add_history(asset.id, 'request_created', f'Създадена заявка за преместване към {to_location.name}.', g.user.id)
        db.session.commit()
        flash('Заявката е изпратена за одобрение.', 'success')
    return redirect(url_for('asset_detail', asset_id=asset.id))


@route('/requests')
@login_required
def requests_list():
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    status = request.args.get('status', '').strip()
    request_type = request.args.get('type', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    direction = request.args.get('direction', 'asc').lower().strip()
    if direction not in ('asc', 'desc'):
        direction = 'asc'
    query = TransferRequest.query.options(
        joinedload(TransferRequest.asset),
        joinedload(TransferRequest.from_location),
        joinedload(TransferRequest.to_location),
        joinedload(TransferRequest.requested_by),
    )
    query = apply_request_scope(query, g.user)

    request_summary = {
        'total': query.count(),
        'pending': query.filter_by(status='pending').count(),
        'approved': query.filter_by(status='approved').count(),
        'rejected': query.filter_by(status='rejected').count(),
    }
    if status in REQUEST_STATUS_META:
        query = query.filter_by(status=status)
    if request_type in ['transfer', 'scrap']:
        query = query.filter_by(request_type=request_type)
    sort_map = {
        'newest': [TransferRequest.created_at],
        'oldest': [TransferRequest.created_at],
        'status': [TransferRequest.status],
        'type': [TransferRequest.request_type],
    }
    columns = sort_map.get(sort, sort_map['newest'])
    if sort == 'newest':
        order_by = (TransferRequest.created_at.desc(),)
    elif sort == 'oldest':
        order_by = (TransferRequest.created_at.asc(),)
    else:
        order_by = tuple(col.desc() if direction == 'desc' else col.asc() for col in columns)
    pagination = query.order_by(*order_by).paginate(page=page, per_page=15, error_out=False)
    filters = {'status': status, 'type': request_type, 'sort': sort, 'direction': direction}
    request_permissions = {
        item.id: {
            'approve': can_approve_request(g.user, item),
            'reject': can_reject_request(g.user, item),
            'delete': False,
        }
        for item in pagination.items
    }
    return render_template('requests.html', items=pagination.items, pagination=pagination, filters=filters,
                           request_summary=request_summary, request_permissions=request_permissions,
                           can_process_requests=any(
                               permissions['approve'] or permissions['reject']
                               for permissions in request_permissions.values()
                           ))


@route('/requests/<int:req_id>/<action>', methods=['POST'])
@login_required
@sensitive_rate_limited
def request_action(req_id, action):
    req = TransferRequest.query.get_or_404(req_id)
    if req.status != 'pending':
        flash('Тази заявка вече е обработена.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    if action == 'approve':
        if not can_approve_request(g.user, req):
            abort(403)
        asset = req.asset
        update_asset_status(asset, req.to_location)
        req.status = 'approved'
        req.approved_by_id = g.user.id
        req.processed_at = datetime.utcnow()
        add_history(asset.id, 'request_approved', f'Одобрено преместване към {req.to_location.name}.', g.user.id)
        db.session.commit()
        app.logger.info('request_approved actor_id=%s request_id=%s asset_id=%s', g.user.id, req.id, req.asset_id)
        flash('Заявката е одобрена.', 'success')
    elif action == 'reject':
        if not can_reject_request(g.user, req):
            abort(403)
        req.status = 'rejected'
        req.approved_by_id = g.user.id
        req.processed_at = datetime.utcnow()
        add_history(req.asset_id, 'request_rejected', f'Отказана заявка към {req.to_location.name}.', g.user.id)
        db.session.commit()
        app.logger.info('request_rejected actor_id=%s request_id=%s asset_id=%s', g.user.id, req.id, req.asset_id)
        flash('Заявката е отказана.', 'success')
    return redirect(request.referrer or url_for('admin_panel'))


@route('/admin')
@login_required
@roles_required(ROLE_SUPERUSER)
def admin_panel():
    return redirect(url_for('users_manage'))


@route('/users', methods=['GET'])
@login_required
@roles_required(ROLE_SUPERUSER)
def users_manage():
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    direction = request.args.get('direction', 'asc').lower().strip()
    if direction not in ('asc', 'desc'):
        direction = 'asc'
    users_query = visible_users_query(g.user, User.query)
    user_summary = {
        'total': users_query.count(),
        'active': users_query.filter_by(is_active=True).count(),
        'inactive': users_query.filter_by(is_active=False).count(),
    }
    if role_filter in ROLE_META:
        users_query = users_query.filter_by(role=role_filter)
    if status_filter == 'active':
        users_query = users_query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        users_query = users_query.filter_by(is_active=False)
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    sort_map = {
        'newest': [User.is_active, User.id],
        'oldest': [User.is_active, User.id],
        'name': [User.is_active, User.full_name],
        'role': [User.is_active, User.role, User.full_name],
        'status': [User.is_active, User.role, User.full_name],
        'location': [User.is_active, User.assigned_location_id, User.full_name],
    }
    columns = sort_map.get(sort, sort_map['name'])
    if sort == 'newest':
        order_by = (User.is_active.desc(), User.id.desc())
    elif sort == 'oldest':
        order_by = (User.is_active.desc(), User.id.asc())
    else:
        order_by = tuple(col.desc() if direction == 'desc' else col.asc() for col in columns)
    pagination = (
        users_query
        .options(selectinload(User.assigned_location), selectinload(User.managed_locations))
        .order_by(*order_by)
        .paginate(page=page, per_page=20, error_out=False)
    )
    users = pagination.items
    locations = assignable_locations_for_user(g.user)
    all_locations = Location.query.filter(Location.is_active.is_(True)).order_by(Location.name).all()
    user_permissions = {
        user.id: {
            'view': can_view_user(g.user, user),
            'edit': can_manage_user(g.user, user),
            'toggle': can_toggle_user(g.user, user),
            'delete': can_delete_user(g.user, user),
            'change_role': can_change_user_role(g.user, user, user.role),
        }
        for user in users
    }
    return render_template('users.html', users=users, locations=locations, all_locations=all_locations,
                           filters={'role': role_filter, 'status': status_filter, 'sort': sort, 'direction': direction}, user_summary=user_summary,
                           pagination=pagination, user_permissions=user_permissions,
                           can_create_user=can_create_user(g.user))


@route('/users/new', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_USER_PLUS, ROLE_SUPERUSER)
def users_new():
    if request.method == 'POST':
        payload = validate_user_payload(request.form, creating=True)
        if payload is None:
            return redirect(url_for('users_new'))
        if not can_create_user_role(g.user, payload['role']):
            flash('Нямате право да създавате потребител с тази роля.', 'error')
            return redirect(url_for('users_new'))
        requested_location_ids = []
        if payload['assigned_location_id']:
            requested_location_ids.append(payload['assigned_location_id'])
        requested_location_ids.extend(payload['team_location_ids'])
        if not user_can_assign_locations(g.user, requested_location_ids):
            flash('Нямате право да назначавате потребител към избраните обекти.', 'error')
            return redirect(url_for('users_new'))

        user = User(
            full_name=payload['full_name'],
            email=payload['email'],
            role=payload['role'],
            assigned_location_id=payload['assigned_location_id'] if payload['role'] not in MULTI_LOCATION_ROLES else None,
            manager_id=g.user.id if g.user.role == ROLE_USER_PLUS else None,
            is_active=True,
            phone_number=payload['phone_number'],
        )
        user.set_password(payload['password'])
        db.session.add(user)
        try:
            db.session.flush()
            apply_user_location_assignments(
                user,
                assigned_location_id=payload['assigned_location_id'],
                team_location_ids=payload['team_location_ids'],
                assigned_location_provided=True,
            )
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Вече има потребител с този имейл.', 'error')
            return redirect(url_for('users_new'))
        flash('Потребителят е създаден.', 'success')
        return redirect(url_for('users_manage'))

    locations = assignable_locations_for_user(g.user)
    all_locations = Location.query.filter(Location.is_active.is_(True)).order_by(Location.name).all()
    editable_roles = [role for role in ROLE_META if can_create_user_role(g.user, role)]
    return render_template(
        'user_form.html',
        user=None,
        locations=locations,
        all_locations=all_locations,
        editable_roles=editable_roles,
        is_new=True,
        can_change_user_assignments=True,
    )


@route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
@sensitive_rate_limited
def user_toggle(user_id):
    target = User.query.get_or_404(user_id)
    if not can_toggle_user(g.user, target):
        flash('Нямате право да управлявате този потребител.', 'error')
        return redirect(url_for('users_manage'))
    target.is_active = not target.is_active
    db.session.commit()
    app.logger.info('user_toggle actor_id=%s target_id=%s active=%s', g.user.id, target.id, target.is_active)
    flash('Статусът на потребителя е променен.', 'success')
    return redirect(url_for('users_manage'))


@route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_USER_PLUS, ROLE_SUPERUSER)
def user_edit(user_id):
    target = User.query.get_or_404(user_id)
    if not can_manage_user(g.user, target):
        flash('Нямате право да редактирате този потребител.', 'error')
        return redirect(url_for('users_manage'))

    if request.method == 'POST':
        payload = validate_user_payload(request.form, creating=False, target=target)
        if payload is None:
            return redirect(url_for('user_edit', user_id=target.id))

        if not can_change_user_role(g.user, target, payload['role']):
            flash('Нямате право да задавате тази роля.', 'error')
            return redirect(url_for('user_edit', user_id=target.id))

        if g.user.role == ROLE_SUPERUSER:
            target.role = payload['role']
            target.is_active = request.form.get('is_active') == 'on'

        target.full_name = payload['full_name']
        target.email = payload['email']
        target.phone_number = payload['phone_number']
        if g.user.role == ROLE_SUPERUSER:
            requested_location_ids = []
            if payload['assigned_location_id']:
                requested_location_ids.append(payload['assigned_location_id'])
            requested_location_ids.extend(payload['team_location_ids'])
            if not user_can_assign_locations(g.user, requested_location_ids):
                flash('Нямате право да назначавате потребител към избраните обекти.', 'error')
                return redirect(url_for('user_edit', user_id=target.id))

        new_password = request.form.get('password', '').strip()
        if new_password:
            if len(new_password) < 8:
                flash('Новата парола трябва да е поне 8 символа.', 'error')
                return redirect(url_for('user_edit', user_id=target.id))
            target.set_password(new_password)

        try:
            if g.user.role == ROLE_SUPERUSER and (
                payload['team_location_ids_provided'] or payload['assigned_location_provided']
            ):
                apply_user_location_assignments(
                    target,
                    assigned_location_id=payload['assigned_location_id'],
                    team_location_ids=payload['team_location_ids'],
                    assigned_location_provided=payload['assigned_location_provided'],
                )
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Вече има потребител с този имейл.', 'error')
            return redirect(url_for('user_edit', user_id=target.id))

        flash('Профилът е обновен.', 'success')
        return redirect(url_for('users_manage'))

    locations = assignable_locations_for_user(g.user)
    all_locations = Location.query.filter(Location.is_active.is_(True)).order_by(Location.name).all()
    return render_template(
        'user_form.html',
        user=target,
        locations=locations,
        all_locations=all_locations,
        editable_roles=list(ROLE_META.keys()) if g.user.role == ROLE_SUPERUSER else None,
        can_change_user_assignments=g.user.role == ROLE_SUPERUSER,
    )


@route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
@sensitive_rate_limited
def user_delete(user_id):
    target = User.query.get_or_404(user_id)
    if not can_delete_user(g.user, target):
        flash('Нямате право да изтриете този потребител.', 'error')
        return redirect(url_for('users_manage'))
    target.managed_locations = []
    target.assigned_location = None
    target.manager = None
    clear_user_links(target.id)
    app.logger.info('user_delete actor_id=%s target_id=%s email=%s', g.user.id, target.id, target.email)
    db.session.delete(target)
    db.session.commit()
    flash('Потребителят е изтрит.', 'success')
    return redirect(url_for('users_manage'))


@route('/locations', methods=['GET'])
@login_required
def locations_list():
    q = request.args.get('q', '').strip()
    location_type = request.args.get('type', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    direction = request.args.get('direction', 'asc').lower().strip()
    if direction not in ('asc', 'desc'):
        direction = 'asc'
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    query = (
        Location.query
        .options(selectinload(Location.technical_lead), selectinload(Location.technicians))
    )
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            Location.name.ilike(like),
            Location.city.ilike(like),
            Location.address.ilike(like),
            Location.gps_location.ilike(like),
            Location.courier_locations.ilike(like),
            Location.type.ilike(like),
            Location.technical_lead.has(User.full_name.ilike(like)),
            Location.technicians.any(User.full_name.ilike(like)),
        ))
    if location_type in LOCATION_META:
        query = query.filter_by(type=location_type)
    sort_map = {
        'newest': [Location.is_active, Location.id],
        'oldest': [Location.is_active, Location.id],
        'name': [Location.is_active, Location.name],
        'type': [Location.is_active, Location.type, Location.name],
    }
    columns = sort_map.get(sort, sort_map['newest'])
    if sort == 'newest':
        order_by = (Location.is_active.desc(), Location.id.desc())
    elif sort == 'oldest':
        order_by = (Location.is_active.desc(), Location.id.asc())
    else:
        order_by = tuple(col.desc() if direction == 'desc' else col.asc() for col in columns)
    pagination = query.order_by(*order_by).paginate(page=page, per_page=20, error_out=False)
    locations = pagination.items
    location_team_counts = {
        location.id: len(get_location_team(location))
        for location in locations
    }
    asset_counts = dict(
        db.session.query(Asset.current_location_id, func.count(Asset.id))
        .group_by(Asset.current_location_id)
        .all()
    )
    location_summary = {
        'total': Location.query.count(),
        'warehouse': Location.query.filter_by(type=LOC_WAREHOUSE).count(),
        'site': Location.query.filter_by(type=LOC_SITE).count(),
        'service': Location.query.filter_by(type=LOC_SERVICE).count(),
        'scrap': Location.query.filter_by(type=LOC_SCRAP).count(),
    }
    return render_template('locations.html', locations=locations, asset_counts=asset_counts,
                           location_team_counts=location_team_counts,
                           filters={'q': q, 'type': location_type, 'sort': sort, 'direction': direction}, location_summary=location_summary,
                           pagination=pagination, location_minimal_types=LOCATION_MINIMAL_TYPES,
                           can_create_location=can_manage_location(g.user),
                           can_edit_location=can_manage_location(g.user))


@route('/locations/<int:location_id>')
@login_required
def location_detail(location_id):
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    per_page = 10
    location = (
        Location.query
        .options(joinedload(Location.technical_lead), joinedload(Location.technicians))
        .get_or_404(location_id)
    )
    if not can_view_location(g.user, location):
        abort(403)
    team_users = get_location_team(location)
    asset_query = (
        Asset.query
        .options(joinedload(Asset.current_location), joinedload(Asset.created_by))
        .filter_by(current_location_id=location.id)
        .order_by(Asset.created_at.desc())
    )
    pagination = asset_query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('location_detail.html', location=location, assets=pagination.items, pagination=pagination,
                           location_minimal_types=LOCATION_MINIMAL_TYPES, team_users=team_users,
                           team_count=len(team_users),
                           can_edit_location=can_manage_location(g.user, location),
                           can_archive_location=can_manage_location(g.user, location) and location.is_active,
                           can_unarchive_location=can_manage_location(g.user, location) and not location.is_active,
                           can_delete_location=can_manage_location(g.user, location),
                           can_manage_location_team=can_manage_location(g.user, location),
                           can_manage_location_manager=can_manage_location(g.user, location))


@route('/locations/<int:location_id>/archive', methods=['POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
@sensitive_rate_limited
def location_archive(location_id):
    location = Location.query.get_or_404(location_id)
    if location.is_active:
        location.is_active = False
        remove_location_from_user_profiles(location)
        db.session.commit()
        app.logger.info('location_archive actor_id=%s location_id=%s name=%s', g.user.id, location.id, location.name)
        flash('Обектът е архивиран.', 'success')
    else:
        flash('Обектът вече е архивиран.', 'error')
    return redirect(request.referrer or url_for('location_detail', location_id=location.id))


@route('/locations/<int:location_id>/unarchive', methods=['POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
@sensitive_rate_limited
def location_unarchive(location_id):
    location = Location.query.get_or_404(location_id)
    if not location.is_active:
        location.is_active = True
        db.session.commit()
        app.logger.info('location_unarchive actor_id=%s location_id=%s name=%s', g.user.id, location.id, location.name)
        flash('Обектът е върнат от архив.', 'success')
    else:
        flash('Обектът вече е активен.', 'error')
    return redirect(request.referrer or url_for('location_detail', location_id=location.id))


@route('/locations/<int:location_id>/delete', methods=['POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
@sensitive_rate_limited
def location_delete(location_id):
    location = Location.query.get_or_404(location_id)
    location.technicians = []
    location.technical_lead = None
    clear_location_links(location.id)
    app.logger.info('location_delete actor_id=%s location_id=%s name=%s', g.user.id, location.id, location.name)
    db.session.delete(location)
    db.session.commit()
    flash('Обектът е изтрит.', 'success')
    return redirect(url_for('locations_list'))


@route('/locations/new', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
def location_new():
    if request.method == 'POST':
        name = request.form['name'].strip()
        location_type = request.form['type']
        technician_ids = [int(t_id) for t_id in request.form.getlist('technicians') if t_id]
        technician_ids = filter_location_team_ids(None, technician_ids)
        is_minimal = location_type in LOCATION_MINIMAL_TYPES
        technical_lead_id = filter_location_lead_id(
            None,
            int(request.form.get('technical_lead_id')) if request.form.get('technical_lead_id') else None,
        )

        if not name:
            flash('Името на обекта е задължително.', 'error')
            return redirect(url_for('location_new'))

        location = Location(
            name=name,
            type=location_type,
            city=request.form.get('city', '').strip() if not is_minimal else None,
            address=request.form.get('address', '').strip() if not is_minimal else None,
            gps_location=request.form.get('gps_location', '').strip() if not is_minimal else None,
            courier_locations=request.form.get('courier_locations', '').strip() if not is_minimal else None,
            technical_lead_id=technical_lead_id if not is_minimal and location_type not in LOCATION_NO_LEAD_TYPES else None,
        )

        db.session.add(location)
        try:
            sync_location_team(location, technician_ids if not is_minimal else [])
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Вече има обект с това име.', 'error')
            return redirect(url_for('location_new'))
        flash('Обектът е създаден.', 'success')
        return redirect(url_for('locations_list'))

    field_users = selectable_location_team_users()
    lead_users = User.query.filter(User.role.in_([ROLE_USER_PLUS, ROLE_USER, ROLE_SUPERUSER]), User.is_active.is_(True)).order_by(
        User.full_name).all()
    return render_template('location_form.html', location_meta=LOCATION_META, field_users=field_users,
                           lead_users=lead_users, location=None, selected_technician_ids=[],
                           location_minimal_types=LOCATION_MINIMAL_TYPES)


@route('/uploads/asset-image', methods=['POST'])
@login_required
@sensitive_rate_limited
def upload_asset_image():
    asset_id = request.form.get('asset_id', type=int) or request.args.get('asset_id', type=int)
    if not asset_id:
        return jsonify({'ok': False, 'error': 'Липсва asset_id.'}), 400
    asset = db.session.get(Asset, asset_id)
    if not asset:
        return jsonify({'ok': False, 'error': 'Активът не е намерен.'}), 404
    if not can_upload_asset_image(g.user, asset):
        app.logger.warning('asset_image_upload_denied actor_id=%s asset_id=%s ip=%s', g.user.id, asset.id, get_client_ip())
        return jsonify({'ok': False, 'error': 'Нямате право да качвате снимки към актив.'}), 403
    uploaded_file = request.files.get('image_file')
    try:
        image_url = save_asset_image_upload(uploaded_file)
    except ValueError as exc:
        app.logger.warning('asset_image_upload_failed actor_id=%s asset_id=%s error=%s', g.user.id, asset.id, str(exc))
        return jsonify({'ok': False, 'error': str(exc)}), 400
    if not image_url:
        return jsonify({'ok': False, 'error': 'Няма подаден файл.'}), 400
    return jsonify({'ok': True, 'image_url': image_url})


@route('/search')
@login_required
def global_search():
    q = request.args.get('q', '').strip()
    if not q:
        return redirect(url_for('dashboard'))
    page = max(request.args.get('page', 1, type=int) or 1, 1)

    search_terms = {q}
    lat_variant = transliterate_cyr_to_lat(q)
    cyr_variant = transliterate_lat_to_cyr(q)
    if lat_variant and lat_variant != q:
        search_terms.add(lat_variant)
    if cyr_variant and cyr_variant != q:
        search_terms.add(cyr_variant)

    likes = [f'%{term}%' for term in search_terms if term]

    def apply_multi_like(query, columns):
        if not likes:
            return query
        filters = []
        for like in likes:
            filters.append(or_(*[column.ilike(like) for column in columns]))
        return query.filter(or_(*filters))

    asset_query = (
        Asset.query
        .options(joinedload(Asset.current_location), joinedload(Asset.created_by))
        .order_by(Asset.created_at.desc())
    )
    asset_query = apply_multi_like(asset_query, [
        Asset.inventory_number,
        Asset.name,
        Asset.alias_name,
        Asset.brand,
        Asset.model,
        Asset.serial_number,
        Asset.invoice_number,
        Asset.supplier_company,
        Asset.notes,
    ])
    location_query = (
        Location.query
        .options(joinedload(Location.technical_lead))
        .order_by(Location.is_active.desc(), Location.name.asc())
    )
    location_query = apply_multi_like(location_query, [
        Location.name,
        Location.city,
        Location.address,
        Location.gps_location,
        Location.courier_locations,
        Location.type,
    ])
    user_query = (
        User.query
        .options(joinedload(User.assigned_location))
        .order_by(User.is_active.desc(), User.full_name.asc())
    )
    user_query = visible_users_query(g.user, user_query)
    user_query = apply_multi_like(user_query, [
        User.full_name,
        User.email,
        User.phone_number,
        User.role,
    ])

    assets = asset_query.limit(25).all()
    locations = location_query.limit(25).all()
    users = user_query.limit(25).all()
    results = {'assets': assets, 'locations': locations, 'users': users}
    result_counts = {
        'assets': len(assets),
        'locations': len(locations),
        'users': len(users),
        'total': len(assets) + len(locations) + len(users),
    }
    return render_template('search.html', query=q, results=results, result_counts=result_counts)


@route('/locations/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
def location_edit(location_id):
    location = Location.query.get_or_404(location_id)
    if request.method == 'POST':
        name = request.form['name'].strip()
        technician_ids = [int(t_id) for t_id in request.form.getlist('technicians') if t_id]
        technician_ids = filter_location_team_ids(location, technician_ids)
        is_minimal = request.form['type'] in LOCATION_MINIMAL_TYPES
        technical_lead_id = filter_location_lead_id(
            location,
            int(request.form.get('technical_lead_id')) if request.form.get('technical_lead_id') else None,
        )

        if not name:
            flash('Името на обекта е задължително.', 'error')
            return redirect(url_for('location_edit', location_id=location.id))

        location.name = name
        location.type = request.form['type']
        location.city = request.form.get('city', '').strip() if not is_minimal else None
        location.address = request.form.get('address', '').strip() if not is_minimal else None
        location.gps_location = request.form.get('gps_location', '').strip() if not is_minimal else None
        location.courier_locations = request.form.get('courier_locations', '').strip() if not is_minimal else None
        location.technical_lead_id = technical_lead_id if not is_minimal and request.form['type'] not in LOCATION_NO_LEAD_TYPES else None

        try:
            sync_location_team(location, technician_ids if not is_minimal else [])
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Вече има обект с това име.', 'error')
            return redirect(url_for('location_edit', location_id=location.id))
        flash('Обектът е обновен.', 'success')
        return redirect(url_for('locations_list'))

    field_users = selectable_location_team_users(location)
    lead_users = User.query.filter(User.role.in_([ROLE_USER_PLUS, ROLE_USER, ROLE_SUPERUSER]), User.is_active.is_(True)).order_by(
        User.full_name).all()
    if location.technical_lead and location.technical_lead.id not in {user.id for user in lead_users}:
        lead_users.append(location.technical_lead)
        lead_users = sorted(lead_users, key=lambda user: user.full_name.lower())
    return render_template('location_form.html', location_meta=LOCATION_META, field_users=field_users,
                           lead_users=lead_users, location=location,
                           selected_technician_ids=[user.id for user in get_location_team(location)],
                           location_minimal_types=LOCATION_MINIMAL_TYPES)


@route('/assets/<int:asset_id>/move', methods=['GET'])
@login_required
def asset_move(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if not can_move_asset(g.user, asset):
        flash('Нямате право да стартирате преместване за този актив.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    locations = Location.query.filter(Location.is_active.is_(True), Location.id != asset.current_location_id).order_by(Location.name.asc()).all()
    can_direct = {location.id: can_direct_transfer(g.user, asset, location) for location in locations}
    return render_template(
        'asset_move.html',
        asset=asset,
        locations=locations,
        location_meta=LOCATION_META,
        can_direct=can_direct,
        can_move_asset=True,
    )


@route('/assets/<int:asset_id>/service/new', methods=['GET', 'POST'])
@login_required
def asset_service_new(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if not can_add_service_record(g.user, asset):
        flash('Нямате право да добавяте сервизен запис към този актив.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    if request.method == 'POST':
        problem = request.form.get('problem', '').strip()
        action_taken = request.form.get('action_taken', '').strip()
        if not problem or not action_taken:
            flash('Проблем и извършено действие са задължителни.', 'error')
            return redirect(url_for('asset_service_new', asset_id=asset.id))
        try:
            invoice_image_path = save_service_invoice_image(request.files.get('invoice_image'))
            record = AssetServiceRecord(
                asset_id=asset.id,
                service_date=parse_service_date(request.form.get('service_date')),
                problem=problem,
                action_taken=action_taken,
                service_provider=request.form.get('service_provider', '').strip() or None,
                price=parse_service_price(request.form.get('price')),
                notes=append_service_invoice_marker(request.form.get('notes', '').strip(), invoice_image_path),
                created_by_id=g.user.id,
            )
            db.session.add(record)
            db.session.add(AssetHistory(
                asset_id=asset.id,
                action='service_added',
                details=f'Добавен сервизен запис: {record.problem}.',
                performed_by_id=g.user.id,
            ))
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
            return redirect(url_for('asset_service_new', asset_id=asset.id))
        flash('Сервизният запис е добавен.', 'success')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    return render_template('asset_service_form.html', asset=asset, record=None, is_new=True, today=date.today().isoformat())


@route('/assets/<int:asset_id>/service/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
def asset_service_edit(asset_id, record_id):
    asset = Asset.query.get_or_404(asset_id)
    record = AssetServiceRecord.query.filter_by(id=record_id, asset_id=asset.id).first_or_404()
    if not can_edit_service_record(g.user, record):
        flash('Нямате права да редактирате този сервизен запис.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    if request.method == 'POST':
        problem = request.form.get('problem', '').strip()
        action_taken = request.form.get('action_taken', '').strip()
        if not problem or not action_taken:
            flash('Проблем и извършено действие са задължителни.', 'error')
            return redirect(url_for('asset_service_edit', asset_id=asset.id, record_id=record.id))
        try:
            invoice_image_path = save_service_invoice_image(request.files.get('invoice_image'))
            if invoice_image_path:
                previous_invoice_path = extract_service_invoice_path(record.notes)
                if previous_invoice_path and previous_invoice_path != invoice_image_path:
                    delete_upload_if_unreferenced(previous_invoice_path, excluding_service_record_ids=[record.id])
            record.service_date = parse_service_date(request.form.get('service_date'))
            record.problem = problem
            record.action_taken = action_taken
            record.service_provider = request.form.get('service_provider', '').strip() or None
            record.price = parse_service_price(request.form.get('price'))
            existing_invoice = extract_service_invoice_path(record.notes)
            record.notes = append_service_invoice_marker(request.form.get('notes', '').strip(), invoice_image_path or existing_invoice)
            db.session.add(AssetHistory(
                asset_id=asset.id,
                action='service_updated',
                details=f'Редактиран сервизен запис от {record.service_date.strftime("%d.%m.%Y")}.',
                performed_by_id=g.user.id,
            ))
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
            return redirect(url_for('asset_service_edit', asset_id=asset.id, record_id=record.id))
        flash('Сервизният запис е обновен.', 'success')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    return render_template('asset_service_form.html', asset=asset, record=record, is_new=False, today=date.today().isoformat())


@route('/assets/<int:asset_id>/service/<int:record_id>', methods=['GET'])
@login_required
def asset_service_detail(asset_id, record_id):
    asset = Asset.query.get_or_404(asset_id)
    record = AssetServiceRecord.query.filter_by(id=record_id, asset_id=asset.id).first_or_404()
    if not can_view_service_record(g.user, record):
        abort(403)
    return render_template(
        'asset_service_detail.html',
        asset=asset,
        record=record,
        can_edit_service_record=can_edit_service_record(g.user, record),
        can_delete_service_record=can_delete_service_record(g.user, record),
    )


@route('/assets/<int:asset_id>/service/<int:record_id>/delete', methods=['POST'])
@login_required
@sensitive_rate_limited
def asset_service_delete(asset_id, record_id):
    asset = Asset.query.get_or_404(asset_id)
    record = AssetServiceRecord.query.filter_by(id=record_id, asset_id=asset.id).first_or_404()
    if not can_delete_service_record(g.user, record):
        flash('Нямате права да изтриете този сервизен запис.', 'error')
        return redirect(url_for('asset_detail', asset_id=asset.id))
    deleted_problem = record.problem
    invoice_path = extract_service_invoice_path(record.notes)
    db.session.delete(record)
    if invoice_path:
        delete_upload_if_unreferenced(invoice_path, excluding_service_record_ids=[record.id])
    db.session.add(AssetHistory(
        asset_id=asset.id,
        action='service_deleted',
        details=f'Изтрит сервизен запис от {deleted_problem}.',
        performed_by_id=g.user.id,
    ))
    db.session.commit()
    flash('Сервизният запис е изтрит.', 'success')
    return redirect(url_for('asset_detail', asset_id=asset.id))


@route('/assets/<int:asset_id>/delete', methods=['POST'])
@login_required
@roles_required(ROLE_SUPERUSER)
@sensitive_rate_limited
def asset_delete(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    image_paths = [image.file_path for image in asset.images]
    service_records = AssetServiceRecord.query.filter_by(asset_id=asset_id).all()
    service_record_ids = [record.id for record in service_records]
    service_invoice_paths = [extract_service_invoice_path(record.notes) for record in service_records if extract_service_invoice_path(record.notes)]
    deleted_requests = TransferRequest.query.filter_by(asset_id=asset_id).delete(synchronize_session=False)
    deleted_history = AssetHistory.query.filter_by(asset_id=asset_id).delete(synchronize_session=False)
    deleted_service_records = AssetServiceRecord.query.filter_by(asset_id=asset_id).delete(synchronize_session=False)
    app.logger.info('asset_delete actor_id=%s asset_id=%s inventory=%s', g.user.id, asset.id, asset.inventory_number)
    db.session.delete(asset)
    db.session.commit()
    for image_path in image_paths:
        delete_upload_if_unreferenced(image_path)
    for invoice_path in service_invoice_paths:
        delete_upload_if_unreferenced(invoice_path, excluding_service_record_ids=service_record_ids)
    flash(f'Машината е изтрита успешно. Премахнати са {deleted_requests} заявки, {deleted_history} записи от историята и {deleted_service_records} сервизни записи.', 'success')
    return redirect(url_for('assets'))


def validate_password_change_form():
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')
    if not password:
        return None, None, 'Въведете нова парола.'
    if not password_confirm:
        return None, None, 'Потвърдете новата парола.'
    if password != password_confirm:
        return None, None, 'Паролите не съвпадат.'
    if len(password) < 8:
        return None, None, 'Паролата трябва да е поне 8 символа.'
    if not password.strip():
        return None, None, 'Паролата не може да бъде само интервали.'
    return password, password_confirm, None


def update_user_password(target_user, password, actor_user, *, is_self_change):
    target_user.set_password(password)
    db.session.commit()
    if is_self_change:
        app.logger.info('password_change actor_id=%s target_id=%s self_change=true', actor_user.id, target_user.id)
        flash('Паролата е обновена успешно.', 'success')
    else:
        app.logger.info(
            'password_change actor_id=%s target_id=%s actor_role=%s target_role=%s self_change=false',
            actor_user.id,
            target_user.id,
            actor_user.role,
            target_user.role,
        )
        flash('Паролата на потребителя е обновена успешно.', 'success')


@route('/profile/password', methods=['GET', 'POST'])
@login_required
def profile_password():
    if request.method == 'POST':
        password, _, error = validate_password_change_form()
        if error:
            flash(error, 'error')
            return redirect(url_for('profile_password'))
        update_user_password(g.user, password, g.user, is_self_change=True)
        return redirect(url_for('profile'))
    return render_template('password_form.html', back_url=url_for('profile'))


@route('/users/<int:user_id>/password', methods=['GET', 'POST'])
@login_required
def user_password(user_id):
    if g.user.role != ROLE_SUPERUSER:
        app.logger.warning(
            'permission_denied user_id=%s role=%s endpoint=%s required_roles=%s',
            g.user.id,
            g.user.role,
            request.endpoint,
            ROLE_SUPERUSER,
        )
        abort(403)

    target_user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        password, _, error = validate_password_change_form()
        if error:
            flash(error, 'error')
            return redirect(url_for('user_password', user_id=target_user.id))
        update_user_password(target_user, password, g.user, is_self_change=False)
        return redirect(url_for('user_profile', user_id=target_user.id))
    return render_template('password_form.html', back_url=url_for('user_profile', user_id=target_user.id))


@template_filter('dt')
def format_dt(value):
    if not value:
        return '-'
    return value.strftime('%d.%m.%Y %H:%M')


@template_filter('eur')
def format_currency_eur(value):
    """Форматира парична стойност в евро: 1 240.00 €."""
    try:
        amount = float(value if value not in (None, '') else 0)
    except (TypeError, ValueError):
        amount = 0.0
    # Български формат: интервал за хилядите, точка за десетичните.
    formatted = f'{amount:,.2f}'.replace(',', ' ')
    return f'{formatted} €'


@context_processor
def inject_service_invoice_helpers():
    return {
        'service_invoice_path': extract_service_invoice_path,
        'strip_service_invoice_marker': strip_service_invoice_marker,
    }


@errorhandler(403)
def handle_forbidden(error):
    app.logger.warning(
        'http_403 path=%s endpoint=%s user_id=%s ip=%s',
        request.path,
        request.endpoint,
        getattr(getattr(g, 'user', None), 'id', None),
        get_client_ip(),
    )
    return render_template('error.html', error_code=403, title='Достъпът е отказан', message='Нямате права за тази страница или операция.'), 403


@errorhandler(400)
def handle_bad_request(error):
    app.logger.warning(
        'http_400 path=%s endpoint=%s user_id=%s ip=%s',
        request.path,
        request.endpoint,
        getattr(getattr(g, 'user', None), 'id', None),
        get_client_ip(),
    )
    return render_template('error.html', error_code=400, title='Невалидна заявка', message='Заявката не може да бъде обработена. Обновете страницата и опитайте отново.'), 400


@errorhandler(404)
def handle_not_found(error):
    app.logger.info('http_404 path=%s ip=%s', request.path, get_client_ip())
    return render_template('error.html', error_code=404, title='Страницата не е намерена', message='Търсеният ресурс не съществува или е премахнат.'), 404


@errorhandler(500)
def handle_server_error(error):
    db.session.rollback()
    app.logger.exception(
        'http_500 path=%s endpoint=%s user_id=%s ip=%s',
        request.path,
        request.endpoint,
        getattr(getattr(g, 'user', None), 'id', None),
        get_client_ip(),
    )
    return render_template('error.html', error_code=500, title='Вътрешна грешка', message='Възникна неочаквана грешка. Опитайте отново по-късно.'), 500


@errorhandler(429)
def handle_rate_limit(error):
    if request.endpoint == 'upload_asset_image' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': False, 'error': 'Твърде много заявки. Опитайте отново след малко.'}), 429
    return render_template('error.html', error_code=429, title='Твърде много заявки', message='Направени са твърде много заявки. Изчакайте малко и опитайте отново.'), 429


@errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(error):
    max_request_size = configured_max_request_size()
    if request.endpoint == 'upload_asset_image' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': False, 'error': f'Заявката е твърде голяма. Максимум {max_request_size // (1024 * 1024)} MB.'}), 413
    flash(f'Файлът или заявката са твърде големи. Максимум {max_request_size // (1024 * 1024)} MB.', 'error')
    return redirect(request.referrer or url_for('dashboard'))
