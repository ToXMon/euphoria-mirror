"""Environment configuration for Kronos production backend."""

import os

# Kronos Model
KRONOS_TOKENIZER = os.getenv("KRONOS_TOKENIZER", "NeoQuasar/Kronos-Tokenizer-base")
KRONOS_MODEL = os.getenv("KRONOS_MODEL", "NeoQuasar/Kronos-small")
KRONOS_MAX_CONTEXT = int(os.getenv("KRONOS_MAX_CONTEXT", "512"))
GPU_ENABLED = os.getenv("GPU_ENABLED", "true").lower() == "true"

# Kronos source path (for importing model classes)
KRONOS_SOURCE_PATH = os.getenv(
    "KRONOS_SOURCE_PATH",
    "/a0/usr/workdir/kronos-main/Kronos-master",
)

# Binance
BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
ETH_SYMBOL = "ETHUSDT"
CACHE_TTL = int(os.getenv("CACHE_TTL", "30"))

# Signals
SIGNAL_CACHE_TTL = int(os.getenv("SIGNAL_CACHE_TTL", "60"))
LAST30DAYS_SCRIPT = os.getenv(
    "LAST30DAYS_SCRIPT",
    "/a0/usr/skills/last30days/scripts/last30days.py",
)

# Edge Score Weights
SOCIAL_WEIGHT = 0.50
KRONOS_WEIGHT = 0.35
ALIGNMENT_WEIGHT = 0.15

EDGE_WEIGHTS = {
    "social": SOCIAL_WEIGHT,
    "kronos": KRONOS_WEIGHT,
    "price_alignment": ALIGNMENT_WEIGHT,
}

# Signal Source Weights
SIGNAL_WEIGHTS = {"reddit": 0.30, "hn": 0.25, "polymarket": 0.25}

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8080,http://localhost:5173,http://localhost:8765",
).split(",")
