from datetime import datetime, time, timedelta

from barage_app.constants import LOC_SERVICE
from barage_app.models import Asset, Location


LONG_SERVICE_STAY_DAYS = 10


def is_service_location(location):
    return bool(location and location.type == LOC_SERVICE)


def service_stay_entry_at(asset):
    if not asset or not is_service_location(getattr(asset, 'current_location', None)):
        return None
    return getattr(asset, 'last_moved_at', None)


def service_stay_days(asset, *, as_of=None):
    entry_at = service_stay_entry_at(asset)
    if not entry_at:
        return None
    current = as_of or datetime.utcnow()
    return max((current.date() - entry_at.date()).days, 0)


def is_long_service_stay(asset, *, as_of=None):
    days = service_stay_days(asset, as_of=as_of)
    return days is not None and days >= LONG_SERVICE_STAY_DAYS


def long_service_stay_cutoff(*, as_of=None):
    current = as_of or datetime.utcnow()
    cutoff_date = current.date() - timedelta(days=LONG_SERVICE_STAY_DAYS - 1)
    return datetime.combine(cutoff_date, time.min)


def apply_long_service_stay_filter(query, *, as_of=None):
    return query.filter(
        Asset.current_location.has(Location.type == LOC_SERVICE),
        Asset.last_moved_at.isnot(None),
        Asset.last_moved_at < long_service_stay_cutoff(as_of=as_of),
    )


def enrich_assets_with_service_stay(assets, *, as_of=None):
    current = as_of or datetime.utcnow()
    for asset in assets:
        days = service_stay_days(asset, as_of=current)
        asset.service_stay_entry_at = service_stay_entry_at(asset)
        asset.service_stay_days = days
        asset.service_stay_is_long = days is not None and days >= LONG_SERVICE_STAY_DAYS
    return assets
