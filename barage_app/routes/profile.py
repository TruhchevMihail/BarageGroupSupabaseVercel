from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('profile_routes', __name__)
ROUTES = [
    ('/login', 'login', legacy.login, ['GET', 'POST']),
    ('/logout', 'logout', legacy.logout, ['POST']),
    ('/profile', 'profile', legacy.profile, ['GET', 'POST']),
    ('/profile/edit', 'profile_edit', legacy.profile_edit, ['GET', 'POST']),
    ('/profile/password', 'profile_password', legacy.profile_password, ['GET', 'POST']),
    ('/users/<int:user_id>/profile', 'user_profile', legacy.user_profile, None),
    ('/users/<int:user_id>/password', 'user_password', legacy.user_password, ['GET', 'POST']),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
