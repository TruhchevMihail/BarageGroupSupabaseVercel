from datetime import datetime, timedelta

import app as app_module


def test_long_service_stay_filter_dashboard_badge_detail_and_pagination(client, db, make_user, login):
    service = app_module.Location(name='Сервиз Дълъг', type=app_module.LOC_SERVICE, is_active=True)
    warehouse = app_module.Location(name='Склад', type=app_module.LOC_WAREHOUSE, is_active=True)
    db.session.add_all([service, warehouse])
    db.session.commit()

    admin = make_user(full_name='Admin', email='service-stay-admin@example.com', role=app_module.ROLE_SUPERUSER)
    now = datetime.utcnow()
    long_assets = []
    for index in range(16):
        long_assets.append(
            app_module.Asset(
                inventory_number=f'SVC-L-{index:02d}',
                name='Машина в сервиз',
                brand='Brand',
                model='Model',
                current_location_id=service.id,
                status=app_module.STATUS_SERVICE,
                last_moved_at=now - timedelta(days=12),
            )
        )
    short_asset = app_module.Asset(
        inventory_number='SVC-SHORT',
        name='Кратък сервиз',
        brand='Brand',
        model='Model',
        current_location_id=service.id,
        status=app_module.STATUS_SERVICE,
        last_moved_at=now - timedelta(days=5),
    )
    unknown_asset = app_module.Asset(
        inventory_number='SVC-UNKNOWN',
        name='Неизвестен престой',
        brand='Brand',
        model='Model',
        current_location_id=service.id,
        status=app_module.STATUS_SERVICE,
        last_moved_at=None,
    )
    warehouse_asset = app_module.Asset(
        inventory_number='WH-LONG',
        name='Не е сервиз',
        brand='Brand',
        model='Model',
        current_location_id=warehouse.id,
        status=app_module.STATUS_WAREHOUSE,
        last_moved_at=now - timedelta(days=20),
    )
    db.session.add_all([*long_assets, short_asset, unknown_asset, warehouse_asset])
    db.session.commit()

    login(admin)

    dashboard = client.get('/dashboard')
    dashboard_html = dashboard.get_data(as_text=True)
    assert dashboard.status_code == 200
    assert 'Дълъг престой в сервиз' in dashboard_html
    assert 'href="/assets?service_stay=long"' in dashboard_html
    assert '<strong>16</strong>' in dashboard_html

    assets = client.get('/assets?service_stay=long')
    assets_html = assets.get_data(as_text=True)
    assert assets.status_code == 200
    assert 'SVC-L-00' in assets_html
    assert 'Дълъг престой · 12 дни' in assets_html
    assert 'SVC-SHORT' not in assets_html
    assert 'SVC-UNKNOWN' not in assets_html
    assert 'WH-LONG' not in assets_html
    assert 'name="service_stay" value="long"' in assets_html
    assert 'service_stay=long&amp;page=2' in assets_html

    detail = client.get(f'/assets/{long_assets[0].id}')
    detail_html = detail.get_data(as_text=True)
    assert detail.status_code == 200
    assert 'Тази машина е в сервиз от 12 дни' in detail_html

    short_detail = client.get(f'/assets/{short_asset.id}')
    assert 'Тази машина е в сервиз от' not in short_detail.get_data(as_text=True)


def test_update_asset_status_does_not_reset_timestamp_when_location_is_unchanged(db):
    service = app_module.Location(name='Сервиз Timestamp', type=app_module.LOC_SERVICE, is_active=True)
    other_service = app_module.Location(name='Друг Сервиз', type=app_module.LOC_SERVICE, is_active=True)
    db.session.add_all([service, other_service])
    db.session.commit()

    original_timestamp = datetime.utcnow() - timedelta(days=14)
    asset = app_module.Asset(
        inventory_number='SVC-TIME',
        name='Машина',
        brand='Brand',
        model='Model',
        current_location_id=service.id,
        status=app_module.STATUS_SERVICE,
        last_moved_at=original_timestamp,
    )

    app_module.update_asset_status(asset, service)
    assert asset.last_moved_at == original_timestamp

    app_module.update_asset_status(asset, other_service)
    assert asset.last_moved_at > original_timestamp
