"""Nguồn 3: Bảng mã quốc gia ISO 3166-1 kèm phân vùng địa lý của Liên Hợp Quốc (UN M49).

Dùng để làm giàu `gold.dim_country` (tên nước, châu lục, tiểu vùng),
vì dataset booking chỉ có mã alpha-3.
Tải từ repo công khai lukes/ISO-3166-Countries-with-Regional-Codes (giấy phép CC BY-SA 4.0).
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
    log.info("Đang tải %s", SOURCE_URL)
    resp = requests.get(SOURCE_URL, timeout=60)
    resp.raise_for_status()
    target.write_bytes(resp.content)
    log.info("Đã lưu %s (%.1f KB)", target, len(resp.content) / 1e3)
