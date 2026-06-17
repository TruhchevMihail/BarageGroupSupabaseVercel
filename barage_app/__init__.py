import os

from flask import Flask

from barage_app.config import (
    BASE_DIR,
    STATIC_ROOT,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
    configure_app,
    configure_app_logging,
)
from barage_app.extensions import db, migrate


def create_app(test_config=None):
    app = Flask(
        __name__,
        static_folder=STATIC_ROOT,
        static_url_path='/static',
        template_folder=os.path.join(BASE_DIR, 'templates'),
    )
    configure_app(app)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    from barage_app import models  # noqa: F401
    from barage_app import routes

    routes.ensure_storage_configuration()
    configure_app_logging(app)

    if (SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY or SUPABASE_STORAGE_BUCKET) and not routes.supabase_storage_enabled():
        app.logger.warning(
            'supabase_storage_partial_config url=%s bucket=%s local_upload_fallback=true',
            bool(SUPABASE_URL),
            bool(SUPABASE_STORAGE_BUCKET),
        )

    if app.config.get('DATABASE_URL_INVALID'):
        app.logger.warning('database_url_invalid_scheme local_sqlite_fallback=true')

    routes.register_routes(app)
    return app
