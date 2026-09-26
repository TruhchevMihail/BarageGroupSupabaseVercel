from pathlib import Path

import app as app_module


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        name='Телескопичен товарач с много дълго оперативно име',
        brand='Barage',
        model='Compact X',
        serial_number='SERIAL-VERY-LONG-0123456789',
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
        'Табло',
        'Машини и инструменти',
        'Заявки',
        'Обекти и локации',
        'Потребители',
    ):
        assert label in html
    assert 'data-theme-toggle' in html
    assert 'class="theme-toggle-label"' in html
    assert 'aria-expanded="false"' in html


def test_assets_use_compact_seven_column_table_without_status_or_serial(
    client, login, make_user, db
):
    admin = _admin(make_user)
    asset = _asset(db, admin)
    login(admin)
    html = client.get('/assets').get_data(as_text=True)
    assert 'data-density="compact"' in html
    assert 'table-row-action' in html
    assert '>Виж детайли</a>' not in html
    assert 'aria-label="Виж детайли за Телескопичен товарач с много дълго оперативно име"' in html
    assert 'title="Виж детайли"' in html
    assert '<span aria-hidden="true">i</span>' in html
    assert 'class="asset-cell-text truncate-cell"' in html
    assert 'title="Телескопичен товарач с много дълго оперативно име"' in html
    for heading in (
        '№',
        'Тип / име',
        'Още познат като',
        'Марка',
        'Модел',
        'Локация',
    ):
        assert heading in html
    assert '<th class="asset-actions-cell" aria-label="Детайли"></th>' in html
    assert 'class="asset-status-cell"' not in html
    assert 'class="asset-serial-cell"' not in html
    assert '<col class="asset-col-status">' not in html
    assert '<col class="asset-col-serial">' not in html
    assert 'type="submit"' in html
    assert '>Търси</button>' in html

    db.session.delete(asset)
    db.session.commit()
    empty_html = client.get('/assets').get_data(as_text=True)
    assert '<td colspan="7" class="empty">' in empty_html


def test_assets_keep_primary_actions_together_and_put_compact_export_in_filters(
    client, login, make_user
):
    admin = _admin(make_user)
    login(admin)

    html = client.get('/assets').get_data(as_text=True)

    page_actions = html[html.index('<div class="detail-actions">'):html.index('</div>', html.index('<div class="detail-actions">'))]
    assert 'Към таблото' not in page_actions
    assert 'Добави актив' in page_actions
    assert 'export.xlsx' not in page_actions
    assert 'export.csv' not in page_actions
    assert 'Импорт CSV/Excel' not in page_actions

    filter_row = html[html.index('<form method="get"'):html.index('</form>', html.index('<form method="get"'))]
    location_index = filter_row.index('class="assets-location-filter')
    export_index = filter_row.index('aria-label="Експорт в Excel"')
    search_index = filter_row.index('>Търси</button>')
    assert location_index < export_index < search_index
    assert 'data-assets-export' in filter_row
    assert 'aria-hidden="true"' in filter_row
    assert '>Export<' not in filter_row


def test_assets_order_location_filter_by_operational_type_then_name(
    client, login, make_user, db
):
    admin = _admin(make_user)
    locations = [
        app_module.Location(name='ZZ Обект', type='site'),
        app_module.Location(name='AA Обект', type='site'),
        app_module.Location(name='AA Склад', type='warehouse'),
        app_module.Location(name='AA Сервиз', type='service'),
        app_module.Location(name='AA Брак', type='scrap'),
    ]
    db.session.add_all(locations)
    db.session.commit()
    login(admin)

    html = client.get('/assets').get_data(as_text=True)

    positions = {location.name: html.index(location.name) for location in locations}
    assert positions['AA Обект'] < positions['ZZ Обект']
    assert positions['ZZ Обект'] < positions['AA Склад']
    assert positions['AA Склад'] < positions['AA Сервиз']
    assert positions['AA Сервиз'] < positions['AA Брак']


def test_dashboard_keeps_operational_sections(client, login, make_user):
    admin = _admin(make_user)
    login(admin)
    html = client.get('/dashboard').get_data(as_text=True)
    for label in (
        'Общ преглед',
        'Статус на машините',
        'В сервиз',
        'Последно добавени машини',
        'Последни заявки',
    ):
        assert label in html
    assert 'data-main-search' in html


def test_login_keeps_only_explicit_access_fields(client):
    html = client.get('/login').get_data(as_text=True)
    assert 'name="email"' in html
    assert 'name="password"' in html
    assert '>Вход<' in html


def test_asset_form_and_detail_keep_explicit_actions(client, login, make_user, db):
    admin = _admin(make_user)
    asset = _asset(db, admin)
    login(admin)

    form_html = client.get('/assets/new').get_data(as_text=True)
    assert 'Инвентарен №' in form_html
    assert '>Запиши<' in form_html
    assert '>Отказ<' in form_html

    detail_html = client.get(f'/assets/{asset.id}').get_data(as_text=True)
    for action in ('Премести / заявка', 'Добави сервизен запис', 'Редактирай'):
        assert action in detail_html
    assert 'Сериен №' in detail_html
    assert 'SERIAL-VERY-LONG-0123456789' in detail_html
    assert 'data-copyable' in detail_html


def test_asset_detail_orders_daily_actions_and_separates_delete(
    client, login, make_user, db
):
    admin = _admin(make_user)
    asset = _asset(db, admin)
    login(admin)

    html = client.get(f'/assets/{asset.id}').get_data(as_text=True)
    header = html[:html.index('<section')]

    assert header.index('>Назад</a>') < header.index('Премести / заявка')
    assert header.index('Премести / заявка') < header.index('Добави сервизен запис')
    assert header.index('Добави сервизен запис') < header.index('Редактирай')
    assert 'Изтрий' not in header
    assert html.index('Опасна зона') > html.index('История')
    assert 'Изтрий актива' in html[html.index('Опасна зона'):]


def test_locations_use_semantic_types_and_explicit_actions(client, login, make_user, db):
    admin = _admin(make_user)
    db.session.add_all([
        app_module.Location(name='Обект Изток', type='site'),
        app_module.Location(name='Склад Запад', type='warehouse'),
        app_module.Location(name='Сервиз Север', type='service'),
        app_module.Location(name='Брак Юг', type='scrap'),
    ])
    db.session.commit()
    login(admin)

    html = client.get('/locations').get_data(as_text=True)
    for class_name in (
        'location-type-site',
        'location-type-warehouse',
        'location-type-service',
        'location-type-scrap',
    ):
        assert class_name in html
    assert 'Виж детайли' in html
    assert 'data-ajax-link' in html


def test_location_detail_orders_daily_actions_and_separates_delete(
    client, login, make_user, db
):
    admin = _admin(make_user)
    location = app_module.Location(name='Обект за подредба', type='site')
    db.session.add(location)
    db.session.commit()
    login(admin)

    html = client.get(f'/locations/{location.id}').get_data(as_text=True)
    header = html[:html.index('<div class="grid-2">')]

    assert header.index('>Назад</a>') < header.index('Архивирай')
    assert header.index('Архивирай') < header.index('Редактирай')
    assert 'Изтрий' not in header
    left_panel = html[html.index('<div class="grid-2">'):html.index('</section>', html.index('<div class="grid-2">'))]
    assert left_panel.index('Основна информация') < left_panel.index('Екип')
    assert 'Машини на обекта' not in left_panel
    assert html.index('Машини на обекта') > html.index('</section>', html.index('<div class="grid-2">'))
    assert html.index('Опасна зона') > html.index('Машини на обекта')
    assert 'Изтрий обекта' in html[html.index('Опасна зона'):]


def test_users_truncate_long_identity_and_use_explicit_profile_action(
    client, login, make_user, db
):
    admin = _admin(make_user)
    location = app_module.Location(
        name='Изключително дълго име на оперативен строителен обект София',
        type='site',
    )
    db.session.add(location)
    db.session.commit()
    user = make_user(
        full_name='Александър Константинов Димитров с дълго служебно име',
        email='alexander.konstantinov.dimitrov.long@example.test',
        role=app_module.ROLE_USER,
        assigned_location=location,
    )
    login(admin)

    users_html = client.get('/users').get_data(as_text=True)
    assert 'class="user-name user-name-plain truncate-cell"' in users_html
    assert f'title="{user.full_name}"' in users_html
    assert f'title="{user.email}"' in users_html
    assert 'Виж профил' in users_html


def test_users_table_keeps_profile_action_fully_visible():
    css = (PROJECT_ROOT / 'frontend/src/styles/users.css').read_text()

    assert '.users-table col.users-col-status { width: 5%; }' in css
    assert '.users-table col.users-col-actions { width: 11%; }' in css
    assert 'overflow: visible;' in css[css.index('.users-cell-actions {'):]


def test_user_profile_orders_daily_actions_and_separates_delete(
    client, login, make_user
):
    admin = _admin(make_user)
    user = make_user(
        full_name='Потребител за подредба',
        email='ordered-user@example.test',
        role=app_module.ROLE_USER,
    )
    login(admin)

    html = client.get(f'/users/{user.id}/profile').get_data(as_text=True)
    header = html[:html.index('<section')]

    assert header.index('>Назад</a>') < header.index('Изключи')
    assert header.index('Изключи') < header.index('Нова парола')
    assert header.index('Нова парола') < header.index('Редактирай')
    assert 'Изтрий' not in header
    assert html.index('Опасна зона') > html.index('Статус')
    assert 'Изтрий потребителя' in html[html.index('Опасна зона'):]


def test_users_show_status_as_an_accessible_indicator_only(client, login, make_user):
    admin = _admin(make_user)
    make_user(
        full_name='Изключен потребител',
        email='inactive-status@example.test',
        role=app_module.ROLE_USER,
        is_active=False,
    )
    login(admin)

    users_html = client.get('/users').get_data(as_text=True)

    assert 'class="users-status" role="img" aria-label="Активен" title="Активен"' in users_html
    assert 'class="users-status" role="img" aria-label="Изключен" title="Изключен"' in users_html
    assert 'class="status-dot ok" aria-hidden="true"' in users_html
    assert 'class="status-dot off" aria-hidden="true"' in users_html
    assert 'class="users-status-label"' not in users_html


def test_users_table_numbers_rows_across_paginated_pages(client, login, make_user, db):
    admin = _admin(make_user)
    for index in range(20):
        db.session.add(app_module.User(
            full_name=f'Тестов потребител {index + 1:02d}',
            email=f'numbered-user-{index + 1:02d}@example.test',
            password_hash='test-only-password-hash',
            role=app_module.ROLE_USER,
            is_active=True,
        ))
    db.session.commit()
    login(admin)

    second_page_html = client.get('/users?page=2').get_data(as_text=True)

    assert '<th class="users-cell-index">№</th>' in second_page_html
    assert 'class="users-cell-index" data-label="№">21</td>' in second_page_html
