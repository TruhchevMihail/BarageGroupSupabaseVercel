import os

from barage_app import create_app
from barage_app.config import *  # noqa: F403
from barage_app.constants import *  # noqa: F403
from barage_app.extensions import db, migrate
from barage_app.models import *  # noqa: F403
from barage_app.routes import *  # noqa: F403


app = create_app()


if __name__ == '__main__':
    with app.app_context():
        init_database()
        if os.path.exists(BACKFILL_MARKER):
            try:
                changed = backfill_user_locations()
                print(f'Backfilled user locations for {changed} users.')
                os.remove(BACKFILL_MARKER)
            except Exception:
                db.session.rollback()
                raise

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5001'))
    debug_mode = os.environ.get('APP_DEBUG', '').lower() in {'1', 'true', 'yes', 'on'}
    app.run(host=host, port=port, debug=debug_mode)
