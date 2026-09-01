import app as app_module
from werkzeug.security import check_password_hash


def test_self_password_change_success(client, db, make_user, login, default_csrf):
    user = make_user(full_name='Self User', email='self@example.com', role=app_module.ROLE_USER, password='oldpassword1')
    login(user)

    response = client.post(
        '/profile/password',
        data={
            'csrf_token': default_csrf,
            'current_password': 'oldpassword1',
            'password': 'newpassword1',
            'password_confirm': 'newpassword1',
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/profile')

    db.session.refresh(user)
    assert check_password_hash(user.password_hash, 'newpassword1')
    assert not check_password_hash(user.password_hash, 'oldpassword1')


def test_self_password_mismatch(client, db, make_user, login, default_csrf):
    user = make_user(full_name='Self User', email='self2@example.com', role=app_module.ROLE_USER, password='oldpassword1')
    login(user)

    response = client.post(
        '/profile/password',
        data={
            'csrf_token': default_csrf,
            'current_password': 'oldpassword1',
            'password': 'newpassword1',
            'password_confirm': 'differentpassword',
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(user)
    assert check_password_hash(user.password_hash, 'oldpassword1')


def test_self_password_too_short(client, db, make_user, login, default_csrf):
    user = make_user(full_name='Self User', email='self3@example.com', role=app_module.ROLE_USER, password='oldpassword1')
    login(user)

    response = client.post(
        '/profile/password',
        data={
            'csrf_token': default_csrf,
            'current_password': 'oldpassword1',
            'password': 'short',
            'password_confirm': 'short',
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(user)
    assert check_password_hash(user.password_hash, 'oldpassword1')


def test_self_password_change_rejects_wrong_current_password(client, db, make_user, login, default_csrf):
    user = make_user(full_name='Self User', email='self4@example.com', role=app_module.ROLE_USER, password='oldpassword1')
    login(user)

    response = client.post(
        '/profile/password',
        data={
            'csrf_token': default_csrf,
            'current_password': 'wrong-password',
            'password': 'newpassword1',
            'password_confirm': 'newpassword1',
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    db.session.refresh(user)
    assert check_password_hash(user.password_hash, 'oldpassword1')


def test_admin_password_reset_success_and_login_works(client, db, make_user, login, csrf_token, default_csrf):
    admin = make_user(full_name='Admin', email='admin@example.com', role=app_module.ROLE_SUPERUSER, password='adminold1')
    target = make_user(full_name='Target', email='target@example.com', role=app_module.ROLE_USER, password='targetold1')
    login(admin)

    response = client.post(
        f'/users/{target.id}/password',
        data={
            'csrf_token': default_csrf,
            'password': 'targetnew1',
            'password_confirm': 'targetnew1',
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/users/{target.id}/profile')

    db.session.refresh(target)
    assert check_password_hash(target.password_hash, 'targetnew1')

    with client.session_transaction() as session:
        session.pop('user_id', None)
        session.pop('_csrf_token', None)

    login_page_csrf = csrf_token('/login')
    login_response = client.post(
        '/login',
        data={
            'csrf_token': login_page_csrf,
            'email': target.email,
            'password': 'targetnew1',
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 302


def test_non_admin_admin_reset_forbidden(client, db, make_user, login, default_csrf):
    user = make_user(full_name='User', email='user@example.com', role=app_module.ROLE_USER, password='userold1')
    target = make_user(full_name='Target', email='target2@example.com', role=app_module.ROLE_USER, password='targetold1')
    login(user)

    get_response = client.get(f'/users/{target.id}/password')
    assert get_response.status_code == 403

    post_response = client.post(
        f'/users/{target.id}/password',
        data={
            'csrf_token': default_csrf,
            'password': 'targetnew1',
            'password_confirm': 'targetnew1',
        },
        follow_redirects=False,
    )
    assert post_response.status_code == 403
