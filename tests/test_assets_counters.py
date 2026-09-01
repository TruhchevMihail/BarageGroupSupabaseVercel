import re

import app as app_module


def test_asset_type_counters_are_based_on_current_location_type(db):
    warehouse = app_module.Location(name='WH', type=app_module.LOC_WAREHOUSE, is_active=True)
    site = app_module.Location(name='SITE', type=app_module.LOC_SITE, is_active=True)
    service = app_module.Location(name='SERVICE', type=app_module.LOC_SERVICE, is_active=True)
    scrap = app_module.Location(name='SCRAP', type=app_module.LOC_SCRAP, is_active=True)
    db.session.add_all([warehouse, site, service, scrap])
    db.session.commit()

    db.session.add_all([
        app_module.Asset(inventory_number='A-1', name='Машина 1', brand='B', model='M', current_location_id=warehouse.id, status=app_module.STATUS_SITE),
        app_module.Asset(inventory_number='A-2', name='Машина 2', brand='B', model='M', current_location_id=site.id, status=app_module.STATUS_WAREHOUSE),
        app_module.Asset(inventory_number='A-3', name='Машина 3', brand='B', model='M', current_location_id=service.id, status=app_module.STATUS_WAREHOUSE),
        app_module.Asset(inventory_number='A-4', name='Машина 4', brand='B', model='M', current_location_id=scrap.id, status=app_module.STATUS_WAREHOUSE),
        app_module.Asset(inventory_number='A-5', name='Машина 5', brand='B', model='M', current_location_id=None, status=app_module.STATUS_WAREHOUSE),
    ])
    db.session.commit()

    counts = app_module.build_asset_type_counts()
    assert counts['total'] == 5
    assert counts['warehouse'] == 1
    assert counts['site'] == 1
    assert counts['service'] == 1
    assert counts['scrap'] == 1


def test_asset_type_sort_uses_displayed_name_across_pagination(client, db, make_user, login):
    warehouse = app_module.Location(name='Склад сорт', type=app_module.LOC_WAREHOUSE, is_active=True)
    db.session.add(warehouse)
    db.session.commit()
    for index in range(17):
        db.session.add(app_module.Asset(
            inventory_number=str(100 - index),
            name=f'Тип {16 - index:02d}',
            asset_type='Машина',
            brand='B',
            model='M',
            current_location_id=warehouse.id,
            status=app_module.STATUS_WAREHOUSE,
        ))
    db.session.commit()

    viewer = make_user(full_name='Sort Viewer', email='sort-viewer@example.com', role=app_module.ROLE_USER)
    login(viewer)
    response = client.get('/assets?sort=type&direction=asc&page=1')
    displayed_names = re.findall(r'data-type="([^"]+)"', response.get_data(as_text=True))

    assert response.status_code == 200
    assert displayed_names == [f'тип {index:02d}' for index in range(15)]
