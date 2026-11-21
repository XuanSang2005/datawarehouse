"""Source 1: Hotel Booking Demand dataset (~119k bookings, 2 hotels in Portugal, 2015-2017).

Original paper: Antonio, Almeida & Nunes (2019), Data in Brief 22.
Downloaded from the public TidyTuesday mirror (identical to `hotel_bookings.csv` on Kaggle,
but no Kaggle account required).
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

log = logging.getLogger("etl.extract.hotel_bookings")

SOURCE_URL = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
    "master/data/2020/2020-02-11/hotels.csv"
)


def extract(target: Path) -> None:
    log.info("Downloading %s", SOURCE_URL)
    resp = requests.get(SOURCE_URL, timeout=60)
    resp.raise_for_status()
    target.write_bytes(resp.content)
    log.info("Saved %s (%.1f MB)", target, len(resp.content) / 1e6)
