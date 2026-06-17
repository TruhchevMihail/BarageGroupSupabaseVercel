from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('upload_routes', __name__)
ROUTES = [
    ('/uploads/asset-image', 'upload_asset_image', legacy.upload_asset_image, ['POST']),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
