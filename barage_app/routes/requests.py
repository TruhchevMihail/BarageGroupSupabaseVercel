from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('request_routes', __name__)
ROUTES = [
    ('/requests', 'requests_list', legacy.requests_list, None),
    ('/requests/<int:req_id>/<action>', 'request_action', legacy.request_action, ['POST']),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
