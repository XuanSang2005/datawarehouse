"""Source 3: ISO 3166-1 country codes with United Nations geographic regions (UN M49).

Used to enrich `gold.dim_country` (country name, continent, sub-region),
because the booking dataset only has alpha-3 codes.
Downloaded from the public repo lukes/ISO-3166-Countries-with-Regional-Codes (CC BY-SA 4.0 license).
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

log = logging.getLogger("etl.extract.countries")

SOURCE_URL = (
    "https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/"
    "master/all/all.csv"
)


def extract(target: Path) -> None:
    log.info("Downloading %s", SOURCE_URL)
    resp = requests.get(SOURCE_URL, timeout=60)
    resp.raise_for_status()
    target.write_bytes(resp.content)
    log.info("Saved %s (%.1f KB)", target, len(resp.content) / 1e3)
