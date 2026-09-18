from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

import app as app_module


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ('location_type', 'location_name', 'expected_chip'),
    (
        (app_module.LOC_WAREHOUSE, 'Централен склад', 'chip-warehouse'),
        (app_module.LOC_SITE, 'УМР 8 – Куклен', 'chip-site'),
        (app_module.LOC_SERVICE, 'Сервиз Пловдив', 'chip-repair'),
        (app_module.LOC_SCRAP, 'Площадка за брак', 'chip-scrap'),
    ),
)
def test_global_search_asset_badge_uses_current_location_name_and_type(
    client, db, make_user, login, location_type, location_name, expected_chip,
):
    location = app_module.Location(name=location_name, type=location_type, is_active=True)
    db.session.add(location)
    db.session.commit()
    asset = app_module.Asset(
        inventory_number=f'SEARCH-{location_type}',
        name='Тестова машина',
        brand='Barage',
        model='Test',
        current_location_id=location.id,
    )
    db.session.add(asset)
    db.session.commit()
    viewer = make_user(
        full_name='Search Admin',
        email=f'search-{location_type}@example.test',
        role=app_module.ROLE_SUPERUSER,
    )
    login(viewer)

    response = client.get(f'/search?q={asset.inventory_number}')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'<span class="chip {expected_chip}">{location_name}</span>' in html


def test_global_search_asset_without_location_uses_neutral_fallback(client, db, make_user, login):
    asset = app_module.Asset(
        inventory_number='SEARCH-NO-LOCATION',
        name='Машина без локация',
        brand='Barage',
        model='Test',
        current_location_id=None,
    )
    db.session.add(asset)
    db.session.commit()
    viewer = make_user(
        full_name='Fallback Admin',
        email='fallback-admin@example.test',
        role=app_module.ROLE_SUPERUSER,
    )
    login(viewer)

    response = client.get('/search?q=SEARCH-NO-LOCATION')

    assert response.status_code == 200
    assert '<span class="chip chip-neutral">Без локация</span>' in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ('role', 'expected_chip', 'expected_label'),
    (
        (app_module.ROLE_USER, 'chip-role-tech', 'Технически ръководител'),
        (app_module.ROLE_WAREHOUSE_WORKER, 'chip-role-warehouse', 'Складов работник'),
        (app_module.ROLE_USER_PLUS, 'chip-role-lead', 'Проектов ръководител'),
        (app_module.ROLE_SUPERUSER, 'chip-role-admin', 'Администратор'),
    ),
)
def test_global_search_user_badge_uses_role_chip(
    client, make_user, login, role, expected_chip, expected_label,
):
    viewer = make_user(
        full_name='Role Search Admin',
        email='role-search-admin@example.test',
        role=app_module.ROLE_SUPERUSER,
    )
    target = make_user(
        full_name=f'Role Search {role}',
        email=f'role-chip-{role}@example.test',
        role=role,
    )
    login(viewer)

    response = client.get(f'/search?q={target.email}')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'<span class="chip {expected_chip}">{expected_label}</span>' in html


def test_list_card_text_color_rules_exclude_chips():
    layout_css = (PROJECT_ROOT / 'frontend/src/styles/layout.css').read_text(encoding='utf-8')
    cards_css = (PROJECT_ROOT / 'frontend/src/styles/cards.css').read_text(encoding='utf-8')

    assert '.list-card span:not(.chip)' in layout_css
    assert '.list-card span:not(.chip)' in cards_css
    assert 'html[data-theme="dark"] .list-card span:not(.chip)' in layout_css


def test_assets_search_requires_explicit_submit_and_preserves_query(client, db, make_user, login):
    viewer = make_user(
        full_name='Assets Search Admin',
        email='assets-search-admin@example.test',
        role=app_module.ROLE_SUPERUSER,
    )
    db.session.add(app_module.Asset(
        inventory_number='FULL-SEARCH-TEXT',
        name='Пълна дума',
        brand='Barage',
        model='Test',
    ))
    db.session.commit()
    login(viewer)

    response = client.get('/assets?q=Пълна дума')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-assets-filter-form data-ajax-form' in html
    assert 'value="Пълна дума" data-main-search' in html
    assert 'value="Пълна дума" data-list-search' not in html
    assert '<button type="submit" class="btn-primary assets-search-button">Търси</button>' in html

    table_source = (PROJECT_ROOT / 'frontend/src/modules/tableEnhancements.ts').read_text(encoding='utf-8')
    assert "addEventListener('input'" not in table_source
    assert "locationSelect?.addEventListener('change'" in table_source


def test_assets_sort_filter_and_pagination_links_preserve_state(client, db, make_user, login):
    location = app_module.Location(name='Филтриран обект', type=app_module.LOC_SITE, is_active=True)
    db.session.add(location)
    db.session.commit()
    db.session.add_all([
        app_module.Asset(
            inventory_number=f'KEEP-{index:02d}',
            name='Запазено търсене',
            brand='Barage',
            model=f'Model {index:02d}',
            current_location_id=location.id,
        )
        for index in range(17)
    ])
    db.session.commit()
    viewer = make_user(
        full_name='Navigation Admin',
        email='navigation-admin@example.test',
        role=app_module.ROLE_SUPERUSER,
    )
    login(viewer)

    response = client.get(
        f'/assets?q=Запазено търсене&location={location.id}&sort=inventory&direction=asc&page=1'
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-sort-key="model"' in html
    assert 'data-ajax-link' in html
    assert f'location={location.id}' in html
    assert 'q=%D0%97%D0%B0%D0%BF%D0%B0%D0%B7%D0%B5%D0%BD%D0%BE+%D1%82%D1%8A%D1%80%D1%81%D0%B5%D0%BD%D0%B5' in html

    pagination_href = next(
        fragment.split('"', 1)[0]
        for fragment in html.split('href="')[1:]
        if 'page=2' in fragment
    )
    pagination_query = parse_qs(urlsplit(pagination_href.replace('&amp;', '&')).query)
    assert pagination_query['q'] == ['Запазено търсене']
    assert pagination_query['location'] == [str(location.id)]
    assert pagination_query['sort'] == ['inventory']
    assert pagination_query['direction'] == ['asc']
    assert pagination_query['page'] == ['2']
