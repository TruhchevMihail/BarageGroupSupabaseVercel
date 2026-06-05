from __future__ import annotations

import random
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app, db


ASSET_PREFIX = "SEED-ASSET"
HISTORY_PREFIX = "Seed history"
HISTORY_ROWS_PER_ASSET = 40


def find_model(predicate):
    for mapper in db.Model.registry.mappers:
        obj = mapper.class_
        table = getattr(obj, "__table__", None)
        if table is None:
            continue
        if predicate(obj, table):
            return obj
    raise RuntimeError("Could not find matching model")


def pick_model_by_table_keywords(keywords):
    keywords = tuple(k.lower() for k in keywords)

    def predicate(obj, table):
        table_name = getattr(table, "name", "").lower()
        class_name = getattr(obj, "__name__", "").lower()
        return any(k in table_name for k in keywords) or any(k in class_name for k in keywords)

    return find_model(predicate)


def column_names(model):
    return [col.name for col in model.__table__.columns]


def set_if_present(payload, columns, key, value):
    if key in columns and value is not None:
        payload[key] = value


def make_asset_payload(columns, idx):
    payload = {}
    set_if_present(payload, columns, "inventory_number", f"{ASSET_PREFIX}-{idx:03d}")
    set_if_present(payload, columns, "name", f"Seed machine {idx:03d}")
    set_if_present(payload, columns, "brand", random.choice(["Hilti", "Bosch", "Makita", "DeWalt", "Stanley"]))
    set_if_present(payload, columns, "model", f"Model-{idx:03d}")
    set_if_present(payload, columns, "serial_number", f"S{idx:06d}")
    set_if_present(payload, columns, "alias_name", f"Alias {idx:03d}")
    set_if_present(payload, columns, "notes", f"Seeded asset {idx}")
    set_if_present(payload, columns, "created_at", datetime.now(timezone.utc))
    set_if_present(payload, columns, "updated_at", datetime.now(timezone.utc))
    set_if_present(payload, columns, "condition", "good")
    set_if_present(payload, columns, "status", "В склад")
    set_if_present(payload, columns, "active", True)
    return payload


def make_history_payload(columns, asset, idx, user_id=None):
    ts = datetime.now(timezone.utc) - timedelta(minutes=idx)
    payload = {}
    set_if_present(payload, columns, "asset_id", asset.id)
    set_if_present(payload, columns, "created_at", ts)
    set_if_present(payload, columns, "updated_at", ts)
    set_if_present(payload, columns, "timestamp", ts)
    set_if_present(payload, columns, "date", ts.date())
    set_if_present(payload, columns, "action", f"{HISTORY_PREFIX} {idx:03d}")
    set_if_present(payload, columns, "description", f"{HISTORY_PREFIX} for {asset.inventory_number} #{idx:03d}")
    set_if_present(payload, columns, "note", f"{HISTORY_PREFIX} note {idx:03d}")
    set_if_present(payload, columns, "details", f"{HISTORY_PREFIX} details {idx:03d}")
    set_if_present(payload, columns, "performed_by_id", user_id)
    set_if_present(payload, columns, "user_id", user_id)
    set_if_present(payload, columns, "created_by_id", user_id)
    return payload


def main():
    with app.app_context():
        Asset = pick_model_by_table_keywords(["asset"])
        History = pick_model_by_table_keywords(["history", "audit", "log"])
        User = None
        try:
            User = pick_model_by_table_keywords(["user"])
        except Exception:
            User = None

        asset_columns = column_names(Asset)
        history_columns = column_names(History)

        user_id = None
        if User is not None and "id" in column_names(User):
            user = db.session.query(User).order_by(User.id.asc()).first()
            if user is not None:
                user_id = user.id

        created_assets = []
        for idx in range(1, 11):
            inventory = f"{ASSET_PREFIX}-{idx:03d}"
            existing = db.session.query(Asset).filter_by(inventory_number=inventory).first() if "inventory_number" in asset_columns else None
            if existing is not None:
                created_assets.append(existing)
                continue
            asset = Asset(**make_asset_payload(asset_columns, idx))
            db.session.add(asset)
            db.session.flush()
            created_assets.append(asset)

        db.session.flush()

        for asset in created_assets:
            for idx in range(1, HISTORY_ROWS_PER_ASSET + 1):
                db.session.add(History(**make_history_payload(history_columns, asset, idx, user_id=user_id)))

        db.session.commit()
        print(f"Seeded {len(created_assets)} assets and {len(created_assets) * HISTORY_ROWS_PER_ASSET} history rows.")


if __name__ == "__main__":
    main()
