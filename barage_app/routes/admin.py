from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('admin_routes', __name__)
ROUTES = [
    ('/init-db', 'init_db', legacy.init_db, ['POST']),
    ('/admin', 'admin_panel', legacy.admin_panel, None),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
