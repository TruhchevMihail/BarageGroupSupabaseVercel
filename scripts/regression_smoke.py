import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('SECRET_KEY', 'smoke-script-secret')

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as app_module  # noqa: E402


def login_as(client, user):
    with client.session_transaction() as session:
        session['user_id'] = user.id
        session['_csrf_token'] = 'smoke-csrf-token'


def assert_status(response, expected, label):
    if response.status_code != expected:
        raise AssertionError(f'{label}: expected {expected}, got {response.status_code}')


def main():
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite')
    os.close(db_fd)

    app_module.app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        UPLOAD_FOLDER=tempfile.mkdtemp(prefix='smoke-uploads-'),
    )

    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()

        warehouse = app_module.Location(name='Склад Казичене', type=app_module.LOC_WAREHOUSE, is_active=True)
        site = app_module.Location(name='Биотрейд - София', type=app_module.LOC_SITE, is_active=True)
        service = app_module.Location(name='Сервиз', type=app_module.LOC_SERVICE, is_active=True)
        scrap = app_module.Location(name='Брак', type=app_module.LOC_SCRAP, is_active=True)
        app_module.db.session.add_all([warehouse, site, service, scrap])
        app_module.db.session.commit()

        admin = app_module.User(full_name='Admin', email='admin@local', role=app_module.ROLE_SUPERUSER, is_active=True)
        admin.set_password('password123')
        worker = app_module.User(full_name='Worker', email='worker@local', role=app_module.ROLE_USER, is_active=True)
        worker.set_password('password123')
        worker.assigned_location_id = site.id
        worker.managed_locations.append(site)
        app_module.db.session.add_all([admin, worker])
        app_module.db.session.commit()

        assets = [
            app_module.Asset(inventory_number='SM-1', name='Машина 1', brand='B', model='M', current_location_id=warehouse.id, status=app_module.STATUS_WAREHOUSE),
            app_module.Asset(inventory_number='SM-2', name='Машина 2', brand='B', model='M', current_location_id=site.id, status=app_module.STATUS_WAREHOUSE),
            app_module.Asset(inventory_number='SM-3', name='Машина 3', brand='B', model='M', current_location_id=service.id, status=app_module.STATUS_WAREHOUSE),
            app_module.Asset(inventory_number='SM-4', name='Машина 4', brand='B', model='M', current_location_id=scrap.id, status=app_module.STATUS_WAREHOUSE),
        ]
        app_module.db.session.add_all(assets)
        app_module.db.session.commit()

        request_row = app_module.TransferRequest(
            asset_id=assets[0].id,
            from_location_id=warehouse.id,
            to_location_id=site.id,
            status='pending',
            requested_by_id=worker.id,
        )
        app_module.db.session.add(request_row)
        app_module.db.session.commit()

        client = app_module.app.test_client()

        login_as(client, admin)
        assert_status(client.get('/assets'), 200, '/assets admin')
        assert_status(client.get(f'/assets/{assets[1].id}'), 200, '/assets/<id> admin')
        assert_status(client.get('/profile/edit'), 200, '/profile/edit admin')
        assert_status(client.get(f'/users/{admin.id}/edit'), 200, '/users/<admin>/edit admin')
        assert_status(client.get(f'/locations/{site.id}'), 200, '/locations/<id> admin')
        assert_status(client.get('/requests'), 200, '/requests admin')

        no_csrf = client.post('/profile/edit', data={'full_name': admin.full_name, 'email': admin.email}, follow_redirects=False)
        assert_status(no_csrf, 400, 'profile_edit missing csrf')

        login_as(client, worker)
        assert_status(client.get('/profile/edit'), 200, '/profile/edit worker')
        assert_status(client.get(f'/locations/{site.id}'), 200, '/locations/<id> worker')
        denied = client.post(
            f'/requests/{request_row.id}/approve',
            data={'csrf_token': 'smoke-csrf-token'},
            follow_redirects=False,
        )
        assert_status(denied, 403, 'non-admin approve request')

        print('Smoke regression checks passed.')

    try:
        os.remove(db_path)
    except OSError:
        pass


if __name__ == '__main__':
    main()
