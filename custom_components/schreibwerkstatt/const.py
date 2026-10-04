"""Constants for the Schreibwerkstatt integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "schreibwerkstatt"

METRICS_PATH: Final = "/metrics.json"
# Highest /metrics.json contract version this integration understands.
SUPPORTED_SCHEMA: Final = 1

DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600
REQUEST_TIMEOUT: Final = 15

GOAL_METRIC: Final = "sw_user_daily_goal_percent"

# Device names per metric group. "server" metrics live on the main device,
# "user" metrics on one device per user.
GROUP_NAMES: Final = {
    "de": {
        "users": "Benutzer",
        "content": "Inhalt",
        "writing": "Schreiben",
        "jobs": "Jobs",
        "ai": "KI",
        "merge": "Block-Merge",
    },
    "en": {
        "users": "Users",
        "content": "Content",
        "writing": "Writing",
        "jobs": "Jobs",
        "ai": "AI",
        "merge": "Block merge",
    },
}
USER_MODEL: Final = {"de": "Benutzer", "en": "User"}
