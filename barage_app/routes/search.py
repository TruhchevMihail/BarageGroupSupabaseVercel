from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('search_routes', __name__)
ROUTES = [
    ('/search', 'global_search', legacy.global_search, None),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
