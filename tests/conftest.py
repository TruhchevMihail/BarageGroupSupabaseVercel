import os
import re
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault('SECRET_KEY', 'pytest-secret-key')

import app as app_module  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite')
    os.close(db_fd)

    upload_root = tmp_path / 'uploads'
    upload_root.mkdir(parents=True, exist_ok=True)
    invoice_map = tmp_path / 'service_invoice_images.json'
    invoice_map.write_text('{}', encoding='utf-8')

    test_app = app_module.create_app(dict(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        WTF_CSRF_ENABLED=False,
        UPLOAD_FOLDER=str(upload_root),
        SERVICE_INVOICE_MAP=str(invoice_map),
    ))
    app_module.app = test_app
    app_module.UPLOAD_FOLDER = str(upload_root)
    app_module.SERVICE_INVOICE_MAP = str(invoice_map)
    app_module.RATE_LIMIT_BUCKETS.clear()

    with test_app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()
        yield test_app
        app_module.db.session.remove()
        app_module.db.drop_all()

    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return app_module.db


def _extract_csrf_token(html):
    patterns = [
        r'name="csrf_token"\s+value="([^"]+)"',
        r'<meta name="csrf-token" content="([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    raise AssertionError('CSRF token not found in response.')


@pytest.fixture()
def csrf_token(client):
    def _get(path):
        response = client.get(path)
        assert response.status_code == 200
        return _extract_csrf_token(response.get_data(as_text=True))
    return _get


@pytest.fixture()
def make_user(db):
    def _make_user(*, full_name, email, role, password='password123', assigned_location=None, is_active=True):
        user = app_module.User(
            full_name=full_name,
            email=email,
            role=role,
            is_active=is_active,
            assigned_location_id=assigned_location.id if assigned_location else None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    return _make_user


@pytest.fixture()
def login(client):
    def _login(user):
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['_csrf_token'] = 'test-csrf-token'
    return _login


@pytest.fixture()
def default_csrf():
    return 'test-csrf-token'
