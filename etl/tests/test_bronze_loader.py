from pathlib import Path

import pytest

from etl.load.bronze_loader import HeaderMismatchError, check_header


def test_check_header_ok():
    check_header(["a", "b"], ["a", "b"], Path("x.csv"), "bronze.x")


def test_check_header_reports_missing_and_extra():
    with pytest.raises(HeaderMismatchError, match="Missing in CSV: \\['b'\\]"):
        check_header(["a", "c"], ["a", "b"], Path("x.csv"), "bronze.x")
