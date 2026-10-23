import pytest
from parser import (parse_log_record, 
                    parse_access_log, 
                    normalize_timestamp,
                    extract_log_timestamp,
                    parse_syslog_record,
                    parse_log_record_auto)
from datetime import datetime, timezone

def test_parse_json_log_string():
    raw = (
        '{"source": "api", "level": "error", '
        '"message": "Database unavailable"}'
    )

    assert parse_log_record(raw) == {
        "source": "api",
        "level": "ERROR",
        "message": "Database unavailable",
    }


def test_parse_dictionary_with_severity_alias():
    raw = {
        "source": "worker",
        "severity": "warning",
        "message": "Retrying task",
    }

    assert parse_log_record(raw) == {
        "source": "worker",
        "level": "WARNING",
        "message": "Retrying task",
    }


def test_parse_key_value_log():
    raw = (
        'source=api level=ERROR '
        'message="Database connection failed"'
    )

    assert parse_log_record(raw) == {
        "source": "api",
        "level": "ERROR",
        "message": "Database connection failed",
    }


def test_parse_log_rejects_missing_source():
    with pytest.raises(ValueError, match="source"):
        parse_log_record({
            "level": "INFO",
            "message": "Application started",
        })


def test_parse_log_rejects_invalid_level():
    with pytest.raises(ValueError, match="Unsupported log level"):
        parse_log_record({
            "source": "api",
            "level": "UNKNOWN",
            "message": "Something happened",
        })


def test_parse_log_rejects_empty_input():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_log_record("")


def test_parse_log_rejects_invalid_json():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_log_record('{"source": "api"')


def test_parse_access_log_success():
    raw = (
        '192.168.1.10 - - [22/Oct/2026:10:20:30 +0000] '
        '"GET /health HTTP/1.1" 200 123 '
        '"-" "Mozilla/5.0"'
    )

    result = parse_access_log(raw)

    assert result["source"] == "192.168.1.10"
    assert result["level"] == "INFO"
    assert result["method"] == "GET"
    assert result["path"] == "/health"
    assert result["status_code"] == 200
    assert result["bytes_sent"] == 123


def test_parse_access_log_server_error():
    raw = (
        '10.0.0.5 - - [22/Oct/2026:10:20:30 +0000] '
        '"POST /api HTTP/1.1" 503 50 "-" "TestClient"'
    )

    result = parse_access_log(raw)

    assert result["level"] == "ERROR"
    assert result["status_code"] == 503


def test_parse_access_log_rejects_invalid_input():
    import pytest

    with pytest.raises(ValueError, match="Invalid or unsupported"):
        parse_access_log("this is not an access log")

def test_normalize_apache_timestamp_to_utc():
    result = normalize_timestamp("22/Oct/2026:10:20:30 +0000")

    assert result == datetime(
        2026, 10, 22, 10, 20, 30,
        tzinfo=timezone.utc,
    )

def test_normalize_iso_timestamp_to_utc():
    result = normalize_timestamp("2026-10-22T15:50:30+05:30")

    assert result == datetime(
        2026, 10, 22, 10, 20, 30,
        tzinfo=timezone.utc,
    )

def test_normalize_timestamp_rejects_missing_timezone():
    import pytest

    with pytest.raises(ValueError, match="timezone"):
        normalize_timestamp("2026-10-22T10:20:30")

def test_extract_timestamp_field():
    result = extract_log_timestamp({
        "timestamp": "2026-10-22T15:50:30+05:30",
    })

    assert result == datetime(
        2026, 10, 22, 10, 20, 30,
        tzinfo=timezone.utc,
    )


def test_extract_at_timestamp_from_json_string():
    result = extract_log_timestamp(
        '{"@timestamp": "2026-10-22T10:20:30Z"}'
    )

    assert result == datetime(
        2026, 10, 22, 10, 20, 30,
        tzinfo=timezone.utc,
    )


def test_extract_time_alias():
    result = extract_log_timestamp({
        "time": "2026-10-22T10:20:30+00:00",
    })

    assert result == datetime(
        2026, 10, 22, 10, 20, 30,
        tzinfo=timezone.utc,
    )


def test_extract_timestamp_returns_none_when_missing():
    assert extract_log_timestamp({
        "source": "api",
        "level": "INFO",
        "message": "Application started",
    }) is None


def test_extract_timestamp_rejects_invalid_value():
    with pytest.raises(ValueError, match="Unsupported timestamp"):
        extract_log_timestamp({
            "timestamp": "not-a-valid-timestamp",
        })


def test_parse_syslog_record_with_priority_and_pid():
    raw = (
        "<34>Oct 22 10:20:30 server01 "
        "sshd[1234]: Failed password for user"
    )

    result = parse_syslog_record(raw)

    assert result["source"] == "server01"
    assert result["level"] == "CRITICAL"
    assert result["message"] == "Failed password for user"
    assert result["priority"] == 34
    assert result["timestamp"] == "Oct 22 10:20:30"
    assert result["hostname"] == "server01"
    assert result["application"] == "sshd"
    assert result["process_id"] == 1234


def test_parse_syslog_record_with_custom_source():
    raw = "<13>Oct 22 10:20:30 server01 sshd: Login successful"

    result = parse_syslog_record(raw, source_name="linux-server")

    assert result["source"] == "linux-server"
    assert result["level"] == "INFO"
    assert result["application"] == "sshd"
    assert result["process_id"] is None


def test_parse_syslog_record_without_priority():
    raw = "Oct 22 10:20:30 server01 cron[456]: Job completed"

    result = parse_syslog_record(raw)

    assert result["priority"] is None
    assert result["level"] == "INFO"
    assert result["process_id"] == 456
    assert result["message"] == "Job completed"


def test_parse_syslog_record_error_severity():
    raw = "<11>Oct 22 10:20:30 server01 app: Something failed"

    result = parse_syslog_record(raw)

    assert result["priority"] == 11
    assert result["level"] == "ERROR"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "This is not a valid syslog record",
        "<999>Oct 22 10:20:30 server01 app: Invalid priority",
        "<34>Invalid timestamp server01 app: Message",
    ],
)

def test_parse_syslog_record_invalid_input(raw):
    with pytest.raises(ValueError):
        parse_syslog_record(raw)

def test_auto_detect_key_value_log():
    result = parse_log_record_auto(
        "source=server1 level=INFO message=Started"
    )

    assert result["_parser_type"] == "structured"
    assert result["source"] == "server1"


def test_auto_detect_access_log():
    raw = (
        '127.0.0.1 - - [22/Oct/2026:10:20:30 +0000] '
        '"GET /health HTTP/1.1" 200 15 "-" "test-agent"'
    )

    result = parse_log_record_auto(raw)

    assert result["_parser_type"] == "access"
    assert result["method"] == "GET"
    assert result["status_code"] == 200


def test_auto_detect_syslog():
    raw = (
        "<34>Oct 22 10:20:30 server01 "
        "sshd[1234]: Failed password for user"
    )

    result = parse_log_record_auto(raw)

    assert result["_parser_type"] == "syslog"
    assert result["hostname"] == "server01"
    assert result["process_id"] == 1234


def test_auto_detect_invalid_log():

    with pytest.raises(ValueError):
        parse_log_record_auto("this is not a valid log record")


