from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('user_routes', __name__)
ROUTES = [
    ('/users', 'users_manage', legacy.users_manage, ['GET']),
    ('/users/new', 'users_new', legacy.users_new, ['GET', 'POST']),
    ('/users/<int:user_id>/toggle', 'user_toggle', legacy.user_toggle, ['POST']),
    ('/users/<int:user_id>/edit', 'user_edit', legacy.user_edit, ['GET', 'POST']),
    ('/users/<int:user_id>/delete', 'user_delete', legacy.user_delete, ['POST']),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
