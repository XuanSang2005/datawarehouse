"""Source 2: Portuguese national holidays, generated offline with the `holidays` library."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import holidays

log = logging.getLogger("etl.extract.pt_holidays")

# Booking dates in the dataset start in 2013 (max lead_time ~2 years); arrivals end in 2017-08.
YEARS = range(2013, 2019)


def extract(target: Path) -> None:
    pt = holidays.country_holidays("PT", years=YEARS)
    rows = sorted(pt.items())
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["holiday_date", "holiday_name"])
        for day, name in rows:
            writer.writerow([day.isoformat(), name])
    log.info("Generated %d holidays into %s", len(rows), target)
