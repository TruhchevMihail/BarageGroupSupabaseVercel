from html.parser import HTMLParser
from urllib.parse import urlsplit

import pytest

import app as app_module


ALL_ROLES = (
    app_module.ROLE_USER,
    app_module.ROLE_WAREHOUSE_WORKER,
    app_module.ROLE_USER_PLUS,
    app_module.ROLE_SUPERUSER,
)


class InternalLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        candidate = values.get('href') if tag == 'a' else values.get('data-url')
        if not candidate:
            return
        parsed = urlsplit(candidate)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith('/'):
            return
        if parsed.path.startswith('/static/'):
            return
        target = parsed.path
        if parsed.query:
            target = f'{target}?{parsed.query}'
        self.links.add(target)


@pytest.fixture()
def role_world(db, make_user):
    warehouse = app_module.Location(name='Тестов склад', type=app_module.LOC_WAREHOUSE, is_active=True)
    site = app_module.Location(name='Тестов обект', type=app_module.LOC_SITE, is_active=True)
    service = app_module.Location(name='Тестов сервиз', type=app_module.LOC_SERVICE, is_active=True)
    scrap = app_module.Location(name='Тестов брак', type=app_module.LOC_SCRAP, is_active=True)
    db.session.add_all([warehouse, site, service, scrap])
    db.session.commit()

    admin = make_user(
        full_name='Тест Администратор',
        email='admin.preview@example.test',
        role=app_module.ROLE_SUPERUSER,
    )
    lead = make_user(
        full_name='Тест Проектов Ръководител',
        email='lead.preview@example.test',
        role=app_module.ROLE_USER_PLUS,
    )
    technician = make_user(
        full_name='Тест Технически Ръководител',
        email='tech.preview@example.test',
        role=app_module.ROLE_USER,
        assigned_location=site,
    )
    warehouse_worker = make_user(
        full_name='Тест Складов Работник',
        email='warehouse.preview@example.test',
        role=app_module.ROLE_WAREHOUSE_WORKER,
        assigned_location=warehouse,
    )
    inactive = make_user(
        full_name='Тест Изключен Потребител',
        email='inactive.preview@example.test',
        role=app_module.ROLE_USER,
        is_active=False,
    )
    lead.managed_locations.append(site)
    technician.managed_locations.append(site)
    warehouse_worker.managed_locations.append(warehouse)
    technician.manager_id = lead.id
    db.session.commit()

    assets = [
        app_module.Asset(
            inventory_number=f'ROLE-{index}',
            name=name,
            brand='Тест марка',
            model='Тест модел',
            current_location_id=location.id,
            status=status,
            created_by_id=admin.id,
        )
        for index, (name, location, status) in enumerate((
            ('Машина в склад', warehouse, app_module.STATUS_WAREHOUSE),
            ('Машина на обект', site, app_module.STATUS_SITE),
            ('Машина в сервиз', service, app_module.STATUS_SERVICE),
            ('Бракувана машина', scrap, app_module.STATUS_SCRAP),
        ), start=1)
    ]
    db.session.add_all(assets)
    db.session.commit()

    service_record = app_module.AssetServiceRecord(
        asset_id=assets[1].id,
        problem='Тестов проблем',
        action_taken='Тестово действие',
        created_by_id=technician.id,
    )
    transfer_request = app_module.TransferRequest(
        asset_id=assets[0].id,
        from_location_id=warehouse.id,
        to_location_id=site.id,
        request_type='transfer',
        status='pending',
        requested_by_id=technician.id,
    )
    db.session.add_all([service_record, transfer_request])
    db.session.commit()

    return {
        'users': {
            app_module.ROLE_SUPERUSER: admin,
            app_module.ROLE_USER_PLUS: lead,
            app_module.ROLE_USER: technician,
            app_module.ROLE_WAREHOUSE_WORKER: warehouse_worker,
        },
        'inactive': inactive,
        'locations': (warehouse, site, service, scrap),
        'assets': assets,
        'service_record': service_record,
        'request': transfer_request,
    }


def crawl_visible_internal_links(client, start_paths, *, limit=300):
    pending = list(start_paths)
    visited = set()
    failures = []

    while pending and len(visited) < limit:
        path = pending.pop(0)
        route_path = urlsplit(path).path
        if route_path in visited:
            continue
        visited.add(route_path)
        response = client.get(path, follow_redirects=False)
        if response.status_code in {403, 404, 500}:
            failures.append((path, response.status_code))
            continue
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get('Location', '')
            parsed = urlsplit(location)
            if not parsed.netloc and parsed.path.startswith('/'):
                redirect_path = parsed.path + (f'?{parsed.query}' if parsed.query else '')
                if parsed.path not in visited:
                    pending.append(redirect_path)
            continue
        if response.status_code != 200 or not response.content_type.startswith('text/html'):
            continue

        parser = InternalLinkParser()
        parser.feed(response.get_data(as_text=True))
        pending.extend(sorted(link for link in parser.links if urlsplit(link).path not in visited))

    return visited, failures


@pytest.mark.parametrize('role', ALL_ROLES)
def test_all_roles_can_view_users_profiles_and_exports(client, login, role_world, role):
    actor = role_world['users'][role]
    login(actor)

    assets_response = client.get('/assets')
    locations_response = client.get('/locations')
    requests_response = client.get('/requests')
    assert assets_response.status_code == 200
    assert locations_response.status_code == 200
    assert requests_response.status_code == 200
    assets_html = assets_response.get_data(as_text=True)
    locations_html = locations_response.get_data(as_text=True)
    requests_html = requests_response.get_data(as_text=True)
    for asset in role_world['assets']:
        assert asset.name in assets_html
    for location in role_world['locations']:
        assert location.name in locations_html
    assert role_world['request'].asset.inventory_number in requests_html

    users_response = client.get('/users')
    users_html = users_response.get_data(as_text=True)
    assert users_response.status_code == 200
    assert 'href="/users"' in users_html
    assert 'href="/admin"' not in users_html
    for target in (*role_world['users'].values(), role_world['inactive']):
        assert target.full_name in users_html
        profile_response = client.get(f'/users/{target.id}/profile')
        assert profile_response.status_code == 200

    csv_response = client.get('/assets/export.csv')
    xlsx_response = client.get('/assets/export.xlsx')
    assert csv_response.status_code == 200
    assert xlsx_response.status_code == 200
    assert csv_response.mimetype == 'text/csv'
    assert xlsx_response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@pytest.mark.parametrize('role', ALL_ROLES)
def test_visible_internal_link_crawl_has_no_403_404_or_500(client, login, role_world, role):
    login(role_world['users'][role])
    visited, failures = crawl_visible_internal_links(
        client,
        ('/dashboard', '/assets', '/locations', '/requests', '/users', '/search?q=Тест'),
    )

    assert len(visited) < 300, 'Visible-link crawl exceeded its safety limit.'
    assert failures == []


@pytest.mark.parametrize('role', ALL_ROLES)
def test_import_and_action_visibility_matches_role(client, login, role_world, role):
    actor = role_world['users'][role]
    login(actor)

    assets_html = client.get('/assets').get_data(as_text=True)
    users_html = client.get('/users').get_data(as_text=True)
    locations_html = client.get('/locations').get_data(as_text=True)
    requests_html = client.get('/requests').get_data(as_text=True)

    assert 'Експорт Excel' in assets_html
    assert 'Експорт CSV' in assets_html
    if role == app_module.ROLE_SUPERUSER:
        assert 'Импорт CSV/Excel' in assets_html
        assert 'Добави актив' in assets_html
        assert 'Добави обект' in locations_html
        assert 'Одобри' in requests_html
        assert 'Откажи' in requests_html
        assert client.get('/assets/import').status_code == 200
    else:
        assert 'Импорт CSV/Excel' not in assets_html
        assert 'Добави актив' not in assets_html
        assert 'Добави обект' not in locations_html
        assert 'Одобри' not in requests_html
        assert 'Откажи' not in requests_html
        denied_import = client.get('/assets/import', follow_redirects=False)
        assert denied_import.status_code == 302
        assert denied_import.headers['Location'].endswith('/dashboard')

    if role in {app_module.ROLE_SUPERUSER, app_module.ROLE_USER_PLUS}:
        assert 'Създай потребител' in users_html
    else:
        assert 'Създай потребител' not in users_html


def test_project_lead_can_edit_only_subordinate_without_password_reset_link(
    client, db, login, role_world, default_csrf,
):
    lead = role_world['users'][app_module.ROLE_USER_PLUS]
    subordinate = role_world['users'][app_module.ROLE_USER]
    unrelated = role_world['users'][app_module.ROLE_WAREHOUSE_WORKER]
    login(lead)

    subordinate_html = client.get(f'/users/{subordinate.id}/profile').get_data(as_text=True)
    unrelated_html = client.get(f'/users/{unrelated.id}/profile').get_data(as_text=True)
    assert f'/users/{subordinate.id}/edit' in subordinate_html
    assert f'/users/{subordinate.id}/password' not in subordinate_html
    assert f'/users/{unrelated.id}/edit' not in unrelated_html

    original_hash = subordinate.password_hash
    response = client.post(
        f'/users/{subordinate.id}/edit',
        data={
            'csrf_token': default_csrf,
            'full_name': subordinate.full_name,
            'email': subordinate.email,
            'phone_number': subordinate.phone_number or '',
            'password': 'forbidden-password-change',
        },
        follow_redirects=False,
    )
    assert response.status_code == 403
    db.session.refresh(subordinate)
    assert subordinate.password_hash == original_hash


def test_user_search_and_user_only_global_search_are_server_rendered(client, login, role_world):
    viewer = role_world['users'][app_module.ROLE_WAREHOUSE_WORKER]
    target = role_world['users'][app_module.ROLE_USER_PLUS]
    login(viewer)

    users_response = client.get('/users?q=Проектов&role=user_plus&status=active&sort=name&direction=asc')
    users_html = users_response.get_data(as_text=True)
    assert users_response.status_code == 200
    assert target.full_name in users_html
    assert role_world['users'][app_module.ROLE_SUPERUSER].full_name not in users_html
    assert 'name="q"' in users_html
    assert 'value="Проектов"' in users_html

    search_response = client.get('/search?q=lead.preview@example.test')
    search_html = search_response.get_data(as_text=True)
    assert search_response.status_code == 200
    assert '<h2>Потребители</h2>' in search_html
    assert target.full_name in search_html


def test_inactive_user_session_is_invalidated(client, role_world):
    inactive = role_world['inactive']
    with client.session_transaction() as session:
        session['user_id'] = inactive.id
        session['_csrf_token'] = 'test-csrf-token'

    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')
    with client.session_transaction() as session:
        assert 'user_id' not in session


def test_external_referer_is_not_used_for_redirect(client, login, role_world, default_csrf):
    admin = role_world['users'][app_module.ROLE_SUPERUSER]
    location = role_world['locations'][1]
    login(admin)

    response = client.post(
        f'/locations/{location.id}/archive',
        data={'csrf_token': default_csrf},
        headers={'Referer': 'https://attacker.example/phishing'},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/locations/{location.id}')


def test_upload_path_guard_rejects_prefix_sibling(app, tmp_path):
    upload_root = tmp_path / 'uploads'
    sibling = tmp_path / 'uploads-elsewhere' / 'file.png'
    app.config['UPLOAD_FOLDER'] = str(upload_root)

    with app.test_request_context('/'):
        assert app_module.resolve_upload_fs_path(str(sibling)) is None
