import json
import re
from datetime import datetime

VALID_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

ACCESS_LOG_PATTERN = re.compile(
    r'^(?P<client_ip>\S+) \S+ \S+ '
    r'\[(?P<timestamp>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) (?P<protocol>[^"]+)" '
    r'(?P<status>\d{3}) (?P<bytes>\S+)'
    r'(?: "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)")?$'
)


def parse_access_log(raw: str, source_name: str | None = None) -> dict:
    """Parse a common Apache/Nginx combined or basic access log."""

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Access log cannot be empty.")

    match = ACCESS_LOG_PATTERN.match(raw.strip())

    if not match:
        raise ValueError("Invalid or unsupported access log format.")

    data = match.groupdict()

    status_code = int(data["status"])

    if status_code >= 500:
        level = "ERROR"
    elif status_code >= 400:
        level = "WARNING"
    else:
        level = "INFO"

    return {
        "source": source_name or data["client_ip"],
        "level": level,
        "message": (
            f'{data["method"]} {data["path"]} '
            f'{data["protocol"]} {status_code}'
        ),
        "timestamp": data["timestamp"],
        "client_ip": data["client_ip"],
        "method": data["method"],
        "path": data["path"],
        "status_code": status_code,
        "bytes_sent": (
            int(data["bytes"])
            if data["bytes"].isdigit()
            else None
        ),
        "referer": data["referer"],
        "user_agent": data["user_agent"],
    }


def parse_log_record(raw: str | dict) -> dict:
    """
    Parse a structured JSON log or key-value log record
    into a common schema: source, level, message.
    """

    if isinstance(raw, dict):
        record = raw.copy()

    elif isinstance(raw, str):
        raw = raw.strip()

        if not raw:
            raise ValueError("Log record cannot be empty.")

        if raw.startswith("{"):
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON log record.") from exc

            if not isinstance(record, dict):
                raise ValueError("JSON log record must be an object.")

        else:
            record = {}

            pattern = r"""([A-Za-z_][A-Za-z0-9_]*)=(?:"([^"]*)"|'([^']*)'|(\S+))"""

            for match in re.finditer(pattern, raw):
                key = match.group(1).lower()
                value = next(
                    group
                    for group in match.groups()[1:]
                    if group is not None
                )
                record[key] = value

            if not record:
                raise ValueError(
                    "Unsupported log format. Expected JSON or key-value fields."
                )

    else:
        raise ValueError("Log record must be a string or dictionary.")

    normalized_fields = {
        str(key).lower(): value
        for key, value in record.items()
    }

    source = normalized_fields.get("source")
    level = normalized_fields.get(
        "level",
        normalized_fields.get("severity"),
    )
    message = normalized_fields.get("message")

    if not isinstance(source, str) or not source.strip():
        raise ValueError("Log record requires a non-empty source.")

    if not isinstance(level, str):
        raise ValueError("Log record requires a valid level.")

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Log record requires a non-empty message.")

    level = level.strip().upper()

    if level not in VALID_LEVELS:
        raise ValueError(f"Unsupported log level: {level}")

    return {
        "source": source.strip(),
        "level": level,
        "message": message.strip(),
    }


def normalize_timestamp(value: str | datetime) -> datetime:
    """Convert supported timestamps to timezone-aware UTC datetime."""

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        value = value.strip()

        try:

            parsed = datetime.strptime(
                value,
                "%d/%b/%Y:%H:%M:%S %z",
            )
        except ValueError:
            try:
              
                parsed = datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ValueError(
                    f"Unsupported timestamp format: {value}"
                ) from exc
    else:
        raise ValueError("Timestamp must be a string or datetime.")

    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")

    from datetime import timezone
    return parsed.astimezone(timezone.utc)


def extract_log_timestamp(raw: str | dict) -> datetime | None:
    """Extract and normalize a timestamp from a JSON log record."""

    if isinstance(raw, dict):
        record = raw

    elif isinstance(raw, str):
        raw = raw.strip()

        if not raw.startswith("{"):
            return None

        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON log record.") from exc

        if not isinstance(record, dict):
            raise ValueError("JSON log record must be an object.")

    else:
        raise ValueError("Log record must be a string or dictionary.")

    for field in ("timestamp", "@timestamp", "time"):
        if field in record:
            value = record[field]

            if not isinstance(value, (str, datetime)):
                raise ValueError(
                    f"Timestamp field '{field}' must be a string or datetime."
                )

            return normalize_timestamp(value)

    return None

SYSLOG_PATTERN = re.compile(
    r"^(?:<(?P<priority>\d{1,3})>)?"
    r"(?P<timestamp>"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    r")\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<application>[^\s:\[]+)"
    r"(?:\[(?P<process_id>\d+)\])?:\s*"
    r"(?P<message>.*)$"
)


def parse_syslog_record(
    raw: str,
    source_name: str | None = None,
) -> dict:
    """Parse a traditional BSD/RFC 3164-style syslog record."""

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Syslog record must be a non-empty string")

    match = SYSLOG_PATTERN.match(raw.strip())

    if not match:
        raise ValueError("Invalid syslog record format")

    data = match.groupdict()

    priority = (
        int(data["priority"])
        if data["priority"] is not None
        else None
    )
    
    if priority is not None and not 0 <= priority <= 191:
        raise ValueError("Syslog priority must be between 0 and 191")

    severity_levels = {
        0: "CRITICAL",  # Emergency
        1: "CRITICAL",  # Alert
        2: "CRITICAL",  # Critical
        3: "ERROR",     # Error
        4: "WARNING",   # Warning
        5: "INFO",      # Notice
        6: "INFO",      # Informational
        7: "DEBUG",     # Debug
    }

    level = (
        severity_levels[priority % 8]
        if priority is not None
        else "INFO"
    )

    return {
        "source": source_name or data["hostname"],
        "level": level,
        "message": data["message"],
        "priority": priority,
        "timestamp": data["timestamp"],
        "hostname": data["hostname"],
        "application": data["application"],
        "process_id": (
            int(data["process_id"])
            if data["process_id"] is not None
            else None
        ),
    }


def parse_log_record_auto(
    raw: str | dict,
    source_name: str | None = None,
) -> dict:
    """Automatically detect and parse supported log formats."""

    if isinstance(raw, dict):
        return parse_log_record(raw)

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Log record must be a non-empty string or dictionary.")

    errors = []

    parsers = (
        ("structured", lambda: parse_log_record(raw)),
        (
            "access",
            lambda: parse_access_log(raw, source_name=source_name),
        ),
        (
            "syslog",
            lambda: parse_syslog_record(raw, source_name=source_name),
        ),
    )

    for parser_name, parser_func in parsers:
        try:
            parsed = parser_func()
            parsed["_parser_type"] = parser_name
            return parsed
        except ValueError as exc:
            errors.append(f"{parser_name}: {exc}")

    raise ValueError(
        "Unable to detect supported log format. "
        + " | ".join(errors)
    )






