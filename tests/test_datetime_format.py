from datetime import datetime, timezone

import app as app_module


def test_format_dt_displays_utc_timestamp_in_sofia_summer_time():
    assert app_module.format_dt(datetime(2026, 9, 1, 6, 23)) == '01.09.2026 09:23'


def test_format_dt_uses_sofia_winter_offset_and_accepts_aware_values():
    value = datetime(2026, 1, 15, 7, 23, tzinfo=timezone.utc)

    assert app_module.format_dt(value) == '15.01.2026 09:23'
