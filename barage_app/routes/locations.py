from flask import Blueprint

from barage_app.routes import legacy

bp = Blueprint('location_routes', __name__)
ROUTES = [
    ('/locations', 'locations_list', legacy.locations_list, ['GET']),
    ('/locations/<int:location_id>', 'location_detail', legacy.location_detail, None),
    ('/locations/<int:location_id>/archive', 'location_archive', legacy.location_archive, ['POST']),
    ('/locations/<int:location_id>/unarchive', 'location_unarchive', legacy.location_unarchive, ['POST']),
    ('/locations/<int:location_id>/delete', 'location_delete', legacy.location_delete, ['POST']),
    ('/locations/new', 'location_new', legacy.location_new, ['GET', 'POST']),
    ('/locations/<int:location_id>/edit', 'location_edit', legacy.location_edit, ['GET', 'POST']),
]

for rule, endpoint, view_func, methods in ROUTES:
    options = {'endpoint': endpoint, 'view_func': view_func}
    if methods is not None:
        options['methods'] = methods
    bp.add_url_rule(rule, **options)
