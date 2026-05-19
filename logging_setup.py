"""
logging_setup.py — Centralised logging configuration.

Import this FIRST in shptest_app.py (and dashboard.py) before any other
project module so all loggers inherit the handlers configured here.

Three log streams:
  logs/app.log   — startup, cache events, data loading, general INFO+
  logs/audit.log — every HTTP request: IP, method, path, status, duration
  logs/error.log — ERROR and above, with full tracebacks

Logs also echo to stdout so journalctl -u shptest captures them.
Files rotate at 10 MB, keeping 7 backups (~70 MB max on disk).
"""

import logging
import logging.handlers
import os
import sys

# ── Directory ────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ── Formatters ───────────────────────────────────────────────────────────────
_DETAILED = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-5s] %(name)-14s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_SIMPLE = logging.Formatter(
    fmt="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _rotating(filename, level=logging.INFO, fmt=_DETAILED):
    h = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=7,
        encoding="utf-8",
    )
    h.setLevel(level)
    h.setFormatter(fmt)
    return h


def _stream(level=logging.INFO, fmt=_DETAILED):
    h = logging.StreamHandler(sys.stdout)
    h.setLevel(level)
    h.setFormatter(fmt)
    return h


# ── app logger — general application events ──────────────────────────────────
app_log = logging.getLogger("shptest.app")
app_log.setLevel(logging.DEBUG)
app_log.addHandler(_rotating("app.log"))
app_log.addHandler(_stream())          # also visible in journalctl
app_log.propagate = False

# ── audit logger — one line per HTTP request ──────────────────────────────────
audit_log = logging.getLogger("shptest.audit")
audit_log.setLevel(logging.INFO)
audit_log.addHandler(_rotating("audit.log", fmt=_SIMPLE))
audit_log.propagate = False

# ── error logger — exceptions and ERROR-level events ─────────────────────────
error_log = logging.getLogger("shptest.error")
error_log.setLevel(logging.ERROR)
error_log.addHandler(_rotating("error.log"))
error_log.addHandler(_stream(level=logging.ERROR))
error_log.propagate = False

# ── Silence noisy third-party loggers ────────────────────────────────────────
for _noisy in ("werkzeug", "urllib3", "fiona", "shapely", "pyogrio"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

app_log.info("Logging initialised — writing to %s", LOG_DIR)
