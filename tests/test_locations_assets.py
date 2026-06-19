import io

import app as app_module


def test_location_archive_requires_superuser_and_removes_from_profile(client, db, make_user, login, default_csrf):
    location = app_module.Location(name='Архив Обект', type=app_module.LOC_SITE, is_active=True)
    db.session.add(location)
    db.session.commit()

    admin = make_user(full_name='Admin', email='archive-admin@example.com', role=app_module.ROLE_SUPERUSER)
    worker = make_user(full_name='Worker', email='archive-worker@example.com', role=app_module.ROLE_USER, assigned_location=location)
    worker.managed_locations.append(location)
    db.session.commit()

    login(worker)
    denied = client.post(f'/locations/{location.id}/archive', data={'csrf_token': default_csrf}, follow_redirects=False)
    assert denied.status_code == 302

    login(admin)
    allowed = client.post(f'/locations/{location.id}/archive', data={'csrf_token': default_csrf}, follow_redirects=False)
    assert allowed.status_code == 302

    db.session.refresh(location)
    db.session.refresh(worker)
    assert location.is_active is False
    assert worker.assigned_location_id is None
    assert list(worker.managed_locations) == []


def test_asset_badge_status_uses_current_location_type(db):
    warehouse = app_module.Location(name='Склад', type=app_module.LOC_WAREHOUSE, is_active=True)
    site = app_module.Location(name='Обект', type=app_module.LOC_SITE, is_active=True)
    service = app_module.Location(name='Сервиз', type=app_module.LOC_SERVICE, is_active=True)
    scrap = app_module.Location(name='Брак', type=app_module.LOC_SCRAP, is_active=True)
    db.session.add_all([warehouse, site, service, scrap])
    db.session.commit()

    assert app_module.asset_display_status(app_module.Asset(current_location=warehouse)) == app_module.STATUS_WAREHOUSE
    assert app_module.asset_display_status(app_module.Asset(current_location=site)) == app_module.STATUS_SITE
    assert app_module.asset_display_status(app_module.Asset(current_location=service)) == app_module.STATUS_SERVICE
    assert app_module.asset_display_status(app_module.Asset(current_location=scrap)) == app_module.STATUS_SCRAP


def test_location_detail_shows_status_from_location_type(client, db, make_user, login):
    location = app_module.Location(name='Биотрейд - София', type=app_module.LOC_SITE, is_active=True)
    db.session.add(location)
    db.session.commit()

    asset = app_module.Asset(
        inventory_number='LOC-1',
        name='Машина',
        brand='Brand',
        model='Model',
        current_location_id=location.id,
        status=app_module.STATUS_WAREHOUSE,
    )
    viewer = make_user(full_name='Viewer', email='viewer@example.com', role=app_module.ROLE_USER)
    db.session.add(asset)
    db.session.commit()

    login(viewer)
    response = client.get(f'/locations/{location.id}')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'На обект' in html


def test_asset_detail_shows_single_location_badge_without_copyable_object(client, db, make_user, login):
    location = app_module.Location(name='Обект Детайл', type=app_module.LOC_SITE, is_active=True)
    db.session.add(location)
    db.session.commit()

    asset = app_module.Asset(
        inventory_number='DET-1',
        name='Машина',
        brand='Brand',
        model='Model',
        current_location_id=location.id,
        status=app_module.STATUS_SITE,
    )
    viewer = make_user(full_name='Asset Viewer', email='asset-viewer@example.com', role=app_module.ROLE_USER)
    db.session.add(asset)
    db.session.commit()

    login(viewer)
    response = client.get(f'/assets/{asset.id}')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'href="/locations/{location.id}"' in html
    assert 'Обект Детайл</a>' in html
    assert 'data-copy-value="Обект Детайл"' not in html
    assert html.count('Обект Детайл') == 1


def test_upload_endpoint_requires_scope_and_csrf(client, db, make_user, login, default_csrf):
    location = app_module.Location(name='Обект Upload', type=app_module.LOC_SITE, is_active=True)
    foreign_location = app_module.Location(name='Друг Обект', type=app_module.LOC_SITE, is_active=True)
    db.session.add_all([location, foreign_location])
    db.session.commit()

    user = make_user(full_name='Scoped User', email='scoped@example.com', role=app_module.ROLE_USER)
    user.managed_locations.append(location)
    db.session.commit()

    asset_in_scope = app_module.Asset(
        inventory_number='UP-1',
        name='Машина',
        brand='Brand',
        model='Model',
        current_location_id=location.id,
        status=app_module.STATUS_SITE,
    )
    asset_out_scope = app_module.Asset(
        inventory_number='UP-2',
        name='Машина 2',
        brand='Brand',
        model='Model',
        current_location_id=foreign_location.id,
        status=app_module.STATUS_SITE,
    )
    db.session.add_all([asset_in_scope, asset_out_scope])
    db.session.commit()

    login(user)

    missing_csrf = client.post(
        '/uploads/asset-image',
        data={'asset_id': str(asset_in_scope.id), 'image_file': (io.BytesIO(b'\x89PNG\r\n\x1a\n1234'), 'test.png')},
        content_type='multipart/form-data',
    )
    assert missing_csrf.status_code == 400

    forbidden = client.post(
        '/uploads/asset-image',
        data={'asset_id': str(asset_out_scope.id), 'csrf_token': default_csrf, 'image_file': (io.BytesIO(b'\x89PNG\r\n\x1a\n1234'), 'test.png')},
        content_type='multipart/form-data',
    )
    assert forbidden.status_code == 403

    invalid_asset = client.post(
        '/uploads/asset-image',
        data={'asset_id': '999999', 'csrf_token': default_csrf, 'image_file': (io.BytesIO(b'\x89PNG\r\n\x1a\n1234'), 'test.png')},
        content_type='multipart/form-data',
    )
    assert invalid_asset.status_code == 404
