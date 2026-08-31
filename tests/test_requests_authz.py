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


def test_stale_request_is_rejected_without_moving_asset(client, db, make_user, login, default_csrf):
    original_location = app_module.Location(name='Първоначален обект', type=app_module.LOC_SITE, is_active=True)
    current_location = app_module.Location(name='Текущ обект', type=app_module.LOC_SITE, is_active=True)
    requested_location = app_module.Location(name='Заявен обект', type=app_module.LOC_SITE, is_active=True)
    db.session.add_all([original_location, current_location, requested_location])
    db.session.commit()

    admin = make_user(full_name='Stale Approver', email='stale-approver@example.com', role=app_module.ROLE_SUPERUSER)
    requester = make_user(full_name='Stale Requester', email='stale-requester@example.com', role=app_module.ROLE_USER)
    asset = app_module.Asset(
        inventory_number='REQ-STALE',
        name='Машина',
        brand='Brand',
        model='Model',
        current_location_id=current_location.id,
        status=app_module.STATUS_SITE,
    )
    db.session.add(asset)
    db.session.commit()

    transfer_request = app_module.TransferRequest(
        asset_id=asset.id,
        from_location_id=original_location.id,
        to_location_id=requested_location.id,
        status='pending',
        requested_by_id=requester.id,
    )
    db.session.add(transfer_request)
    db.session.commit()

    login(admin)
    response = client.post(
        f'/requests/{transfer_request.id}/approve',
        data={'csrf_token': default_csrf},
        follow_redirects=False,
    )

    assert response.status_code == 302
    db.session.refresh(asset)
    db.session.refresh(transfer_request)
    assert asset.current_location_id == current_location.id
    assert transfer_request.status == 'rejected'
