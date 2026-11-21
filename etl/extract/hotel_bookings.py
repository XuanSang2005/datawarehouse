"""Nguồn 1: Hotel Booking Demand dataset (~119k booking, 2 khách sạn ở Bồ Đào Nha, 2015-2017).

Bài báo gốc: Antonio, Almeida & Nunes (2019), Data in Brief 22.
Tải từ bản mirror công khai của TidyTuesday (giống hệt file `hotel_bookings.csv` trên Kaggle,
nhưng không cần tài khoản Kaggle).
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
    log.info("Đang tải %s", SOURCE_URL)
    resp = requests.get(SOURCE_URL, timeout=60)
    resp.raise_for_status()
    target.write_bytes(resp.content)
    log.info("Đã lưu %s (%.1f MB)", target, len(resp.content) / 1e6)
