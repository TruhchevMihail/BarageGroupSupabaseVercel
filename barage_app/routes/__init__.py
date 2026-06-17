from importlib import import_module

from barage_app.routes.legacy import *  # noqa: F401,F403
from barage_app.routes import legacy

BLUEPRINT_MODULES = (
    import_module('barage_app.routes.dashboard'),
    import_module('barage_app.routes.profile'),
    import_module('barage_app.routes.assets'),
    import_module('barage_app.routes.requests'),
    import_module('barage_app.routes.admin'),
    import_module('barage_app.routes.users'),
    import_module('barage_app.routes.locations'),
    import_module('barage_app.routes.uploads'),
    import_module('barage_app.routes.search'),
)


def _register_legacy_endpoint_aliases(flask_app):
    for module in BLUEPRINT_MODULES:
        for rule, endpoint, view_func, methods in module.ROUTES:
            options = {'endpoint': endpoint, 'view_func': view_func}
            if methods is not None:
                options['methods'] = methods
            flask_app.add_url_rule(rule, **options)


def register_routes(flask_app):
    for view in legacy._BEFORE_REQUESTS:
        flask_app.before_request(view)
    for view in legacy._CONTEXT_PROCESSORS:
        flask_app.context_processor(view)
    for name, view in legacy._TEMPLATE_FILTERS:
        flask_app.add_template_filter(view, name)
    for code_or_exception, view in legacy._ERROR_HANDLERS:
        flask_app.register_error_handler(code_or_exception, view)

    _register_legacy_endpoint_aliases(flask_app)
    for module in BLUEPRINT_MODULES:
        flask_app.register_blueprint(module.bp)
