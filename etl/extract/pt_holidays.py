"""Nguồn 2: Ngày lễ quốc gia Bồ Đào Nha, sinh offline bằng thư viện `holidays`."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import holidays

log = logging.getLogger("etl.extract.pt_holidays")

# Dataset booking có ngày đặt từ 2013 (lead_time tối đa ~2 năm) đến ngày đến 2017-08.
YEARS = range(2013, 2019)


def extract(target: Path) -> None:
    pt = holidays.country_holidays("PT", years=YEARS)
    rows = sorted(pt.items())
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["holiday_date", "holiday_name"])
        for day, name in rows:
            writer.writerow([day.isoformat(), name])
    log.info("Đã sinh %d ngày lễ vào %s", len(rows), target)
