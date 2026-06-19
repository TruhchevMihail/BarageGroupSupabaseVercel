from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('asset_routes', __name__)
ROUTES = [
    ('/assets', 'assets', legacy.assets, None),
    ('/assets/export.csv', 'assets_export_csv', legacy.assets_export_csv, None),
    ('/assets/import', 'assets_import', legacy.assets_import, None),
    ('/assets/import/preview', 'assets_import_preview', legacy.assets_import_preview, ['POST']),
    ('/assets/import/confirm', 'assets_import_confirm', legacy.assets_import_confirm, ['POST']),
    ('/assets/import/template.csv', 'assets_import_template_csv', legacy.assets_import_template_csv, None),
    ('/assets/new', 'asset_new', legacy.asset_new, ['GET', 'POST']),
    ('/assets/<int:asset_id>', 'asset_detail', legacy.asset_detail, None),
    ('/assets/<int:asset_id>/edit', 'asset_edit', legacy.asset_edit, ['GET', 'POST']),
    ('/assets/<int:asset_id>/service', 'asset_service_add', legacy.asset_service_add, ['POST']),
    ('/transfer/<int:asset_id>', 'transfer_asset', legacy.transfer_asset, ['POST']),
    ('/assets/<int:asset_id>/move', 'asset_move', legacy.asset_move, ['GET']),
    ('/assets/<int:asset_id>/service/new', 'asset_service_new', legacy.asset_service_new, ['GET', 'POST']),
    ('/assets/<int:asset_id>/service/<int:record_id>/edit', 'asset_service_edit', legacy.asset_service_edit, ['GET', 'POST']),
    ('/assets/<int:asset_id>/service/<int:record_id>', 'asset_service_detail', legacy.asset_service_detail, ['GET']),
    ('/assets/<int:asset_id>/service/<int:record_id>/delete', 'asset_service_delete', legacy.asset_service_delete, ['POST']),
    ('/assets/<int:asset_id>/delete', 'asset_delete', legacy.asset_delete, ['POST']),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
