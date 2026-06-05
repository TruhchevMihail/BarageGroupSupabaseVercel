import app as app_module


def test_non_admin_cannot_approve_request(client, db, make_user, login, default_csrf):
    from_location = app_module.Location(name='От', type=app_module.LOC_WAREHOUSE, is_active=True)
    to_location = app_module.Location(name='До', type=app_module.LOC_SITE, is_active=True)
    db.session.add_all([from_location, to_location])
    db.session.commit()

    asset = app_module.Asset(
        inventory_number='REQ-1',
        name='Машина',
        brand='Brand',
        model='Model',
        current_location_id=from_location.id,
        status=app_module.STATUS_WAREHOUSE,
    )
    requester = make_user(full_name='Requester', email='requester@example.com', role=app_module.ROLE_USER)
    actor = make_user(full_name='Actor', email='actor@example.com', role=app_module.ROLE_USER)
    db.session.add(asset)
    db.session.commit()

    req = app_module.TransferRequest(
        asset_id=asset.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
        status='pending',
        requested_by_id=requester.id,
    )
    db.session.add(req)
    db.session.commit()

    login(actor)
    response = client.post(f'/requests/{req.id}/approve', data={'csrf_token': default_csrf}, follow_redirects=False)
    assert response.status_code == 403


def test_request_action_missing_csrf_fails(client, db, make_user, login):
    from_location = app_module.Location(name='От 2', type=app_module.LOC_WAREHOUSE, is_active=True)
    to_location = app_module.Location(name='До 2', type=app_module.LOC_SITE, is_active=True)
    db.session.add_all([from_location, to_location])
    db.session.commit()

    asset = app_module.Asset(
        inventory_number='REQ-2',
        name='Машина',
        brand='Brand',
        model='Model',
        current_location_id=from_location.id,
        status=app_module.STATUS_WAREHOUSE,
    )
    admin = make_user(full_name='Approver', email='approver@example.com', role=app_module.ROLE_SUPERUSER)
    requester = make_user(full_name='Requester 2', email='requester2@example.com', role=app_module.ROLE_USER)
    db.session.add(asset)
    db.session.commit()

    req = app_module.TransferRequest(
        asset_id=asset.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
        status='pending',
        requested_by_id=requester.id,
    )
    db.session.add(req)
    db.session.commit()

    login(admin)
    response = client.post(f'/requests/{req.id}/approve', data={}, follow_redirects=False)
    assert response.status_code == 400
