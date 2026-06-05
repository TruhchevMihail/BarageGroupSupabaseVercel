import os
import sys

from flask_migrate import upgrade


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app


with app.app_context():
    upgrade()
    print("Database migrations applied.")
