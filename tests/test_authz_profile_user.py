import app as app_module


def test_admin_self_profile_edit_can_update_assigned_locations(client, db, make_user, login, default_csrf):
    location_a = app_module.Location(name='Обект А', type=app_module.LOC_SITE, is_active=True)
    location_b = app_module.Location(name='Обект Б', type=app_module.LOC_SITE, is_active=True)
    db.session.add_all([location_a, location_b])
    db.session.commit()

    admin = make_user(full_name='Admin User', email='admin@example.com', role=app_module.ROLE_SUPERUSER)
    login(admin)

    response = client.post(
        '/profile/edit',
        data={
            'csrf_token': default_csrf,
            'full_name': admin.full_name,
            'email': admin.email,
            'phone_number': '',
            'assigned_location_id': str(location_a.id),
            'team_location_ids': [str(location_a.id), str(location_b.id)],
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    db.session.refresh(admin)
    managed_ids = {location.id for location in admin.managed_locations}
    assert managed_ids == {location_a.id, location_b.id}
    assert admin.assigned_location_id is None


def test_non_admin_self_profile_edit_cannot_update_assigned_locations(client, db, make_user, login, default_csrf):
    location_a = app_module.Location(name='Обект A', type=app_module.LOC_SITE, is_active=True)
    location_b = app_module.Location(name='Обект B', type=app_module.LOC_SITE, is_active=True)
    db.session.add_all([location_a, location_b])
    db.session.commit()

    user = make_user(
        full_name='Tech User',
        email='tech@example.com',
        role=app_module.ROLE_USER,
        assigned_location=location_a,
    )
    user.managed_locations.append(location_a)
    db.session.commit()

    login(user)
    response = client.post(
        '/profile/edit',
        data={
            'csrf_token': default_csrf,
            'full_name': user.full_name,
            'email': user.email,
            'phone_number': '',
            'assigned_location_id': str(location_b.id),
            'team_location_ids': [str(location_a.id), str(location_b.id)],
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    db.session.refresh(user)
    managed_ids = {location.id for location in user.managed_locations}
    assert managed_ids == {location_a.id}
    assert user.assigned_location_id == location_a.id


def test_profile_edit_missing_csrf_fails(client, db, make_user, login):
    user = make_user(full_name='Profile User', email='profile@example.com', role=app_module.ROLE_SUPERUSER)
    login(user)

    response = client.post(
        '/profile/edit',
        data={'full_name': user.full_name, 'email': user.email, 'phone_number': ''},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_admin_can_edit_other_user_locations_without_clearing_missing_fields(client, db, make_user, login, default_csrf):
    location_a = app_module.Location(name='Локация 1', type=app_module.LOC_SITE, is_active=True)
    location_b = app_module.Location(name='Локация 2', type=app_module.LOC_SITE, is_active=True)
    db.session.add_all([location_a, location_b])
    db.session.commit()

    admin = make_user(full_name='Admin User', email='admin2@example.com', role=app_module.ROLE_SUPERUSER)
    target = make_user(full_name='Target User', email='target@example.com', role=app_module.ROLE_USER, assigned_location=location_a)
    target.managed_locations.extend([location_a, location_b])
    db.session.commit()

    login(admin)
    response = client.post(
        f'/users/{target.id}/edit',
        data={
            'csrf_token': default_csrf,
            'full_name': target.full_name,
            'email': target.email,
            'phone_number': '',
            'role': target.role,
            'is_active': 'on',
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    db.session.refresh(target)
    managed_ids = {location.id for location in target.managed_locations}
    assert managed_ids == {location_a.id, location_b.id}


def test_user_edit_missing_csrf_fails(client, db, make_user, login):
    admin = make_user(full_name='Admin User', email='admin3@example.com', role=app_module.ROLE_SUPERUSER)
    target = make_user(full_name='Target User', email='target2@example.com', role=app_module.ROLE_USER)
    login(admin)

    response = client.post(
        f'/users/{target.id}/edit',
        data={'full_name': target.full_name, 'email': target.email, 'role': target.role},
        follow_redirects=False,
    )
    assert response.status_code == 400
