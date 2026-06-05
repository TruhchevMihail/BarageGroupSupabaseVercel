"""Copy data from the old local SQLite database into Supabase Postgres.

Recommended flow:
  1. Set SECRET_KEY and DATABASE_URL to the Supabase Postgres connection string.
  2. Run migrations: python scripts/run_migrations.py
  3. Copy data: python scripts/migrate_sqlite_to_supabase.py --sqlite app.db --truncate

The script preserves primary keys and then updates Postgres sequences.
It does not upload local image files. Run migrate_uploads_to_supabase.py after this
if you also need to move files from static/uploads to Supabase Storage.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text
from flask_migrate import upgrade

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db, init_database  # noqa: E402

TABLES: list[tuple[str, list[str], str | None]] = [
    (
        "user",
        [
            "id",
            "full_name",
            "email",
            "password_hash",
            "role",
            "assigned_location_id",
            "manager_id",
            "is_active",
            "phone_number",
        ],
        "id",
    ),
    (
        "location",
        [
            "id",
            "name",
            "type",
            "is_active",
            "city",
            "address",
            "gps_location",
            "courier_locations",
            "technical_lead_id",
        ],
        "id",
    ),
    ("location_technicians", ["location_id", "user_id"], None),
    (
        "asset",
        [
            "id",
            "inventory_number",
            "name",
            "category",
            "asset_type",
            "brand",
            "model",
            "serial_number",
            "alias_name",
            "image_url",
            "invoice_number",
            "company_name",
            "purchase_date",
            "supplier_company",
            "warranty",
            "notes",
            "status",
            "condition",
            "current_location_id",
            "responsible_user_id",
            "created_by_id",
            "created_at",
            "last_moved_at",
        ],
        "id",
    ),
    ("asset_image", ["id", "asset_id", "file_path", "created_at"], "id"),
    (
        "transfer_request",
        [
            "id",
            "asset_id",
            "from_location_id",
            "to_location_id",
            "request_type",
            "reason",
            "status",
            "requested_by_id",
            "approved_by_id",
            "created_at",
            "processed_at",
        ],
        "id",
    ),
    ("asset_history", ["id", "asset_id", "action", "details", "performed_by_id", "created_at"], "id"),
    (
        "asset_service_record",
        [
            "id",
            "asset_id",
            "service_date",
            "problem",
            "action_taken",
            "service_provider",
            "price",
            "notes",
            "attachment_url",
            "created_by_id",
            "created_at",
        ],
        "id",
    ),
]

DEFAULTS: dict[str, dict[str, Any]] = {
    "user": {"is_active": True, "phone_number": None, "assigned_location_id": None, "manager_id": None},
    "location": {"is_active": True, "technical_lead_id": None},
    "asset": {"asset_type": "Машина", "condition": "Работи"},
    "transfer_request": {"request_type": "transfer", "status": "pending"},
}

SERIAL_TABLES = [table for table, _columns, pk in TABLES if pk == "id"]
TRUNCATE_SQL = 'TRUNCATE asset_service_record, asset_history, transfer_request, asset_image, asset, location_technicians, location, "user" RESTART IDENTITY CASCADE'


def qident(identifier: str) -> str:
    return '"user"' if identifier == "user" else identifier


def sqlite_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info('{table}')").fetchall()}


def fetch_rows(connection: sqlite3.Connection, table: str, columns: list[str]) -> list[dict[str, Any]]:
    available = sqlite_columns(connection, table)
    if not available:
        print(f"skip missing table: {table}")
        return []
    selected = [column for column in columns if column in available]
    rows = connection.execute(f"SELECT {', '.join(selected)} FROM {table}").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item.update({key: value for key, value in DEFAULTS.get(table, {}).items() if key not in item})
        for column in columns:
            item.setdefault(column, None)
        result.append(item)
    return result


def insert_rows(connection, table: str, columns: list[str], rows: list[dict[str, Any]]):
    if not rows:
        return 0
    quoted_table = qident(table)
    quoted_columns = ", ".join(qident(column) for column in columns)
    values = ", ".join(f":{column}" for column in columns)
    conflict = "ON CONFLICT DO NOTHING"
    statement = text(f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({values}) {conflict}")
    connection.execute(statement, [{column: row.get(column) for column in columns} for row in rows])
    return len(rows)


def update_deferred_foreign_keys(connection, users: list[dict[str, Any]], locations: list[dict[str, Any]]):
    for user in users:
        connection.execute(
            text('UPDATE "user" SET assigned_location_id = :assigned_location_id, manager_id = :manager_id WHERE id = :id'),
            {
                "id": user["id"],
                "assigned_location_id": user.get("assigned_location_id"),
                "manager_id": user.get("manager_id"),
            },
        )
    for location in locations:
        connection.execute(
            text("UPDATE location SET technical_lead_id = :technical_lead_id WHERE id = :id"),
            {"id": location["id"], "technical_lead_id": location.get("technical_lead_id")},
        )


def reset_sequences(connection):
    for table in SERIAL_TABLES:
        quoted = qident(table)
        sequence_table_arg = '\"user\"' if table == "user" else table
        connection.execute(
            text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{sequence_table_arg}', 'id'),
                    GREATEST(COALESCE((SELECT MAX(id) FROM {quoted}), 1), 1),
                    COALESCE((SELECT MAX(id) FROM {quoted}), 0) > 0
                )
                """
            )
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to the configured Supabase/Postgres database.")
    parser.add_argument("--sqlite", default="app.db", help="Path to source SQLite database")
    parser.add_argument("--truncate", action="store_true", help="Empty target tables before import")
    parser.add_argument("--skip-migrations", action="store_true", help="Do not run Alembic upgrade before import")
    return parser.parse_args()


def main():
    args = parse_args()
    sqlite_path = Path(args.sqlite).expanduser().resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row

    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            raise SystemExit("Target DATABASE_URL is not Postgres. Set DATABASE_URL to Supabase before running this script.")
        if not args.skip_migrations:
            upgrade()
        init_database()

        all_rows: dict[str, list[dict[str, Any]]] = {}
        for table, columns, _pk in TABLES:
            all_rows[table] = fetch_rows(source, table, columns)

        user_rows_for_update = [dict(row) for row in all_rows["user"]]
        location_rows_for_update = [dict(row) for row in all_rows["location"]]
        for row in all_rows["user"]:
            row["assigned_location_id"] = None
            row["manager_id"] = None
        for row in all_rows["location"]:
            row["technical_lead_id"] = None

        with db.engine.begin() as connection:
            if args.truncate:
                connection.execute(text(TRUNCATE_SQL))
            for table, columns, _pk in TABLES:
                inserted = insert_rows(connection, table, columns, all_rows[table])
                print(f"{table}: queued {inserted} rows")
            update_deferred_foreign_keys(connection, user_rows_for_update, location_rows_for_update)
            reset_sequences(connection)

    source.close()
    print("SQLite data migration finished.")


if __name__ == "__main__":
    main()
