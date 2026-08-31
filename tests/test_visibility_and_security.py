import app as app_module
from flask import g


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
    assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert response.headers['Permissions-Policy'] == 'camera=(), microphone=(), geolocation=(self)'
    assert "frame-ancestors 'self'" in response.headers['Content-Security-Policy']


def test_untrusted_forwarded_for_is_ignored_by_default(app):
    with app.test_request_context('/', headers={'X-Forwarded-For': '203.0.113.10'}, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        g.user = None
        assert app_module.get_client_ip() == '127.0.0.1'
