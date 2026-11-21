from etl.quality import parse_severity


def test_parse_severity_warning():
    assert parse_severity("-- severity: warning\nSELECT 1") == "warning"


def test_parse_severity_defaults_to_error():
    assert parse_severity("SELECT 1") == "error"
