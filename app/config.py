"""Settings, read from environment variables.

Every setting has a default that works for local development,
so the app runs without any setup.
"""

import os

# Local default is a SQLite file. Docker Compose sets this to PostgreSQL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kyc.db")

# Token needed to create API keys. If empty, key creation is switched off.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Each API key may make this many requests per window.
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
