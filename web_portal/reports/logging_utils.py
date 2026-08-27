import datetime
import json
import logging

_BASE_RECORD_KEYS = set(vars(logging.makeLogRecord({})).keys())


class ReportingJsonFormatter(logging.Formatter):
    """Emits one JSON object per log line, folding in any `extra=` fields
    (user_id, report_name, parameters, elapsed_ms, success, ...) so logs
    stay machine-parseable for whatever ships them (stdout -> log aggregator).
    """

    def format(self, record):
        payload = {
            "timestamp": datetime.datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _BASE_RECORD_KEYS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)
