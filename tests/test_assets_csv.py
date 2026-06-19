import io
import json
from pathlib import Path

import app as app_module


def _asset(inventory_number, *, name='Машина', brand='Brand', model='Model', location=None, status=None):
    return app_module.Asset(
        inventory_number=inventory_number,
        name=name,
        brand=brand,
        model=model,
        current_location_id=location.id if location else None,
        status=status or app_module.STATUS_WAREHOUSE,
    )


def test_authenticated_user_can_export_assets_csv_with_filters(client, db, make_user, login):
    warehouse = app_module.Location(name='Склад CSV', type=app_module.LOC_WAREHOUSE, is_active=True)
    service = app_module.Location(name='Сервиз CSV', type=app_module.LOC_SERVICE, is_active=True)
    db.session.add_all([warehouse, service])
    db.session.commit()
    db.session.add_all([
        _asset('CSV-1', name='Къртач', location=warehouse, status=app_module.STATUS_WAREHOUSE),
        _asset('CSV-2', name='Дрелка', location=service, status=app_module.STATUS_SERVICE),
    ])
    db.session.commit()

    user = make_user(full_name='CSV User', email='csv-user@example.com', role=app_module.ROLE_USER)
    login(user)

    response = client.get('/assets/export.csv?status=В сервиз')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert 'attachment; filename=assets.csv' in response.headers['Content-Disposition']
    assert 'Инвентарен №' in body
    assert 'CSV-2' in body
    assert 'CSV-1' not in body


def test_unauthenticated_user_cannot_export_assets_csv(client):
    response = client.get('/assets/export.csv')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_assets_page_shows_import_only_to_admin(client, db, make_user, login):
    user = make_user(full_name='Regular User', email='regular-assets@example.com', role=app_module.ROLE_USER)
    admin = make_user(full_name='Admin User', email='admin-assets@example.com', role=app_module.ROLE_SUPERUSER)

    login(user)
    user_page = client.get('/assets')
    assert user_page.status_code == 200
    assert 'Експорт CSV' in user_page.get_data(as_text=True)
    assert 'Импорт CSV' not in user_page.get_data(as_text=True)

    login(admin)
    admin_page = client.get('/assets')
    assert admin_page.status_code == 200
    assert 'Импорт CSV' in admin_page.get_data(as_text=True)


def test_non_admin_cannot_access_asset_import(client, db, make_user, login):
    user = make_user(full_name='Import User', email='import-user@example.com', role=app_module.ROLE_USER)
    login(user)
    response = client.get('/assets/import')
    assert response.status_code == 302
    assert '/dashboard' in response.headers['Location']


def test_admin_can_access_asset_import_page(client, db, make_user, login):
    admin = make_user(full_name='Import Admin', email='import-admin@example.com', role=app_module.ROLE_SUPERUSER)
    login(admin)
    response = client.get('/assets/import')
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Качи CSV файл' in html
    assert 'Импортът е достъпен само за администратори.' in html


def test_asset_import_preview_validates_rows_and_does_not_touch_uploads(client, app, db, make_user, login, default_csrf):
    admin = make_user(full_name='Preview Admin', email='preview-admin@example.com', role=app_module.ROLE_SUPERUSER)
    location = app_module.Location(name='Централен склад', type=app_module.LOC_WAREHOUSE, is_active=True)
    db.session.add(location)
    db.session.commit()
    login(admin)

    before_uploads = set(Path(app.config['UPLOAD_FOLDER']).rglob('*'))
    csv_text = (
        '№,name,brand,model,asset_type,current_location\n'
        'IMP-1,Къртач,Bosch,GSH 11,Машина,Централен склад\n'
        'IMP-1,Дубликат,Bosch,GSH 12,Машина,Централен склад\n'
        'IMP-2,Без локация,Bosch,GSH 13,Невалиден,Несъществуваща локация\n'
    )
    response = client.post(
        '/assets/import/preview',
        data={
            'csrf_token': default_csrf,
            'csv_file': (io.BytesIO(csv_text.encode('utf-8')), 'assets.csv'),
        },
        content_type='multipart/form-data',
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Валидни редове' in html
    assert '<strong>1</strong>' in html
    assert 'Дублиран инвентарен № в CSV файла.' in html
    assert 'Невалиден вид актив.' in html
    assert app_module.Asset.query.count() == 0
    assert set(Path(app.config['UPLOAD_FOLDER']).rglob('*')) == before_uploads


def test_asset_import_rejects_non_csv_upload(client, db, make_user, login, default_csrf):
    admin = make_user(full_name='Reject Admin', email='reject-admin@example.com', role=app_module.ROLE_SUPERUSER)
    login(admin)

    response = client.post(
        '/assets/import/preview',
        data={
            'csrf_token': default_csrf,
            'csv_file': (io.BytesIO(b'not csv'), 'assets.txt'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert 'Файлът трябва да бъде CSV.' in response.get_data(as_text=True)
    assert app_module.Asset.query.count() == 0


def test_asset_import_confirm_upserts_valid_rows_without_deleting_assets(client, db, make_user, login, default_csrf):
    admin = make_user(full_name='Confirm Admin', email='confirm-admin@example.com', role=app_module.ROLE_SUPERUSER)
    location = app_module.Location(name='Склад Импорт', type=app_module.LOC_WAREHOUSE, is_active=True)
    db.session.add(location)
    db.session.commit()
    existing = _asset('KEEP-1', name='Стара машина', brand='Old', model='Old', location=location)
    untouched = _asset('KEEP-2', name='Остава', brand='Same', model='Same', location=location)
    db.session.add_all([existing, untouched])
    db.session.commit()
    login(admin)

    payload = json.dumps([
        {
            'inventory_number': 'KEEP-1',
            'name': 'Обновена машина',
            'brand': 'New',
            'model': 'New',
            'asset_type': 'Машина',
            'current_location': 'Склад Импорт',
        },
        {
            'inventory_number': 'NEW-1',
            'name': 'Нова машина',
            'brand': 'Brand',
            'model': 'Model',
            'asset_type': 'Инструмент',
            'current_location': 'Склад Импорт',
        },
    ], ensure_ascii=False)

    response = client.post(
        '/assets/import/confirm',
        data={'csrf_token': default_csrf, 'preview_payload': payload},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert app_module.Asset.query.count() == 3
    db.session.refresh(existing)
    db.session.refresh(untouched)
    created = app_module.Asset.query.filter_by(inventory_number='NEW-1').one()
    assert existing.name == 'Обновена машина'
    assert untouched.name == 'Остава'
    assert created.asset_type == 'Инструмент'
