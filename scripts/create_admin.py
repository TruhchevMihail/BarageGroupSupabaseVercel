"""Create the first Barage Group administrator.

Usage examples:
  SECRET_KEY=... DATABASE_URL=... python scripts/create_admin.py --email admin@example.com
  ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='StrongPass123' python scripts/create_admin.py
"""

import argparse
import os
import sys
from getpass import getpass
from pathlib import Path

from flask_migrate import upgrade

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import ROLE_SUPERUSER, User, app, db, init_database  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Create or repair a superuser account.")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", ""), help="Admin email")
    parser.add_argument("--name", default=os.environ.get("ADMIN_FULL_NAME", "System Admin"), help="Full name")
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", ""), help="Admin password")
    parser.add_argument("--skip-migrations", action="store_true", help="Do not run Alembic upgrade first")
    parser.add_argument("--reset-password", action="store_true", help="Reset password if the email already exists")
    return parser.parse_args()


def main():
    args = parse_args()
    email = (args.email or input("Email: ")).strip().lower()
    full_name = (args.name or input("Full name: ")).strip() or "System Admin"
    password = args.password or getpass("Password: ")

    if not email or "@" not in email:
        raise SystemExit("A valid email is required.")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    with app.app_context():
        if not args.skip_migrations:
            upgrade()
        init_database()

        user = User.query.filter_by(email=email).first()
        if user:
            changed = False
            if user.role != ROLE_SUPERUSER:
                user.role = ROLE_SUPERUSER
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if args.reset_password:
                user.set_password(password)
                changed = True
            if changed:
                db.session.commit()
                print(f"Admin account updated: {email}")
            else:
                print(f"Admin account already exists: {email}")
            return

        user = User(full_name=full_name, email=email, role=ROLE_SUPERUSER, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Admin account created: {email}")


if __name__ == "__main__":
    main()
