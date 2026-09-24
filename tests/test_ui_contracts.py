import app as app_module


def _admin(make_user):
    return make_user(
        full_name='UI Администратор',
        email='ui-admin@example.test',
        role=app_module.ROLE_SUPERUSER,
    )


def _asset(db, admin):
    warehouse = app_module.Location(name='Централен склад', type='warehouse')
    db.session.add(warehouse)
    db.session.flush()
    asset = app_module.Asset(
        inventory_number='UI-001',
        name='Мини багер',
        brand='Barage',
        model='Compact X',
        current_location_id=warehouse.id,
        created_by_id=admin.id,
    )
    db.session.add(asset)
    db.session.commit()
    return asset


def test_login_has_text_labeled_theme_control(client):
    html = client.get('/login').get_data(as_text=True)
    assert 'data-theme-toggle' in html
    assert 'class="theme-toggle-label"' in html
    assert 'Тъмна тема' in html or 'Светла тема' in html


def test_authenticated_shell_uses_explicit_navigation_labels(client, login, make_user):
    admin = _admin(make_user)
    login(admin)
    html = client.get('/dashboard').get_data(as_text=True)
    for label in (
        'Общ преглед',
        'Машини и инструменти',
        'Заявки',
        'Обекти и локации',
        'Потребители',
    ):
        assert label in html
    assert 'data-theme-toggle' in html
    assert 'class="theme-toggle-label"' in html
    assert 'aria-expanded="false"' in html


def test_assets_use_compact_table_and_explicit_action(client, login, make_user, db):
    admin = _admin(make_user)
    _asset(db, admin)
    login(admin)
    html = client.get('/assets').get_data(as_text=True)
    assert 'data-density="compact"' in html
    assert 'table-row-action' in html
    assert 'Виж детайли' in html
    assert 'title="Детайли">⋯</a>' not in html
