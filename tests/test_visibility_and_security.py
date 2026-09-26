import app as app_module
import io
from unittest.mock import patch
from flask import g
from werkzeug.datastructures import FileStorage


def test_all_authenticated_roles_can_view_user_list_and_active_profiles(client, db, make_user, login):
    admin = make_user(
        full_name='Visible Admin',
        email='visible-admin@example.com',
        role=app_module.ROLE_SUPERUSER,
    )
    project_manager = make_user(
        full_name='Visible Project Manager',
        email='visible-project@example.com',
        role=app_module.ROLE_USER_PLUS,
    )
    technician = make_user(
        full_name='Visible Technician',
        email='visible-tech@example.com',
        role=app_module.ROLE_USER,
    )
    inactive_user = make_user(
        full_name='Visible Inactive User',
        email='visible-inactive@example.com',
        role=app_module.ROLE_USER,
        is_active=False,
    )

    for viewer in (project_manager, technician):
        login(viewer)
        response = client.get('/users')
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert admin.full_name in html
        assert project_manager.full_name in html
        assert technician.full_name in html
        assert inactive_user.full_name in html

        profile_response = client.get(f'/users/{admin.id}/profile')
        assert profile_response.status_code == 200
        assert admin.full_name in profile_response.get_data(as_text=True)

        inactive_profile_response = client.get(f'/users/{inactive_user.id}/profile')
        assert inactive_profile_response.status_code == 200


def test_user_visibility_does_not_grant_admin_actions(client, db, make_user, login, default_csrf):
    viewer = make_user(
        full_name='Read Only Viewer',
        email='read-only@example.com',
        role=app_module.ROLE_USER,
    )
    target = make_user(
        full_name='Protected Target',
        email='protected-target@example.com',
        role=app_module.ROLE_USER,
    )
    login(viewer)

    edit_response = client.get(f'/users/{target.id}/edit')
    toggle_response = client.post(
        f'/users/{target.id}/toggle',
        data={'csrf_token': default_csrf},
        follow_redirects=False,
    )

    assert edit_response.status_code == 302
    assert '/dashboard' in edit_response.headers['Location']
    assert toggle_response.status_code == 302
    db.session.refresh(target)
    assert target.is_active is True


def test_inactive_user_session_is_invalidated(client, db, make_user, login):
    user = make_user(
        full_name='Disabled Session',
        email='disabled-session@example.com',
        role=app_module.ROLE_USER,
    )
    login(user)
    user.is_active = False
    db.session.commit()

    response = client.get('/dashboard', follow_redirects=False)

    assert response.status_code == 302
    assert '/login' in response.headers['Location']
    with client.session_transaction() as session:
        assert 'user_id' not in session


def test_security_headers_are_present(client):
    response = client.get('/login')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert response.headers['Permissions-Policy'] == 'camera=(), microphone=(), geolocation=(self)'
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    assert "script-src 'self' 'nonce-" in response.headers['Content-Security-Policy']
    assert "'unsafe-inline'" not in response.headers['Content-Security-Policy'].split('script-src')[1].split(';')[0]
    assert response.headers['Cache-Control'] == 'no-store, private'


def test_rate_limit_returns_429_and_retry_after_for_post(client, csrf_token, app):
    app.config['LOGIN_RATE_LIMIT'] = (2, 60)
    token = csrf_token('/login')
    for _ in range(2):
        assert client.post('/login', data={
            'csrf_token': token, 'email': 'missing@example.test', 'password': 'wrong',
        }).status_code == 200
    blocked = client.post('/login', data={
        'csrf_token': token, 'email': 'missing@example.test', 'password': 'wrong',
    })
    assert blocked.status_code == 429
    assert blocked.headers['Retry-After'] == '60'


def test_global_limit_applies_before_database_work(client, app):
    app.config['TRAFFIC_RATE_LIMIT'] = (2, 60)
    assert client.get('/login').status_code == 200
    assert client.get('/login').status_code == 200
    assert client.get('/login').status_code == 429


def test_rate_limit_keys_cannot_grow_without_bound(app):
    from barage_app.config import RATE_LIMIT_BUCKETS
    from barage_app.routes.legacy import is_rate_limited

    app.config['MAX_RATE_LIMIT_KEYS'] = 3
    for index in range(10):
        with app.test_request_context('/login', environ_base={'REMOTE_ADDR': f'192.0.2.{index + 1}'}):
            assert not is_rate_limited('test', 2, 60)
    assert len(RATE_LIMIT_BUCKETS) <= 3


def test_password_reset_invalidates_existing_session(client, db, make_user, login):
    user = make_user(full_name='Session Reset', email='reset-session@example.test', role=app_module.ROLE_USER)
    login(user)
    assert client.get('/dashboard').status_code == 200
    user.set_password('new-password-strong')
    db.session.commit()
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')


def test_image_upload_rejects_excessive_pixel_count():
    from barage_app.routes.legacy import validate_image_upload

    upload = FileStorage(stream=io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'0' * 512), filename='large.png')
    with patch('barage_app.routes.legacy.Image.open') as open_image:
        open_image.return_value.width = 6000
        open_image.return_value.height = 5000
        try:
            validate_image_upload(upload)
        except ValueError as exc:
            assert 'резолюция' in str(exc)
        else:
            raise AssertionError('An oversized image was accepted')


def test_untrusted_forwarded_for_is_ignored_by_default(app):
    with app.test_request_context('/', headers={'X-Forwarded-For': '203.0.113.10'}, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        g.user = None
        assert app_module.get_client_ip() == '127.0.0.1'
