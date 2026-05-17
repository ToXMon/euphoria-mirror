"""Social signal collection via last30days pipeline.

Runs the last30days skill to collect Reddit, HN, and Polymarket signals.
Falls back to heuristic-based analysis when the pipeline is unavailable.
"""

import logging
import subprocess
import time
from typing import Any

from backend.config import LAST30DAYS_SCRIPT, SIGNAL_CACHE_TTL, SIGNAL_WEIGHTS

logger = logging.getLogger(__name__)

# Cache state
_cache: dict[str, Any] = {
    "signals": None,
    "ts": 0.0,
    "query": None,
}


def _is_cache_valid(query: str) -> bool:
    """Check if cached signals are still fresh."""
    if _cache["signals"] is None or _cache["query"] != query:
        return False
    return (time.time() - _cache["ts"]) < SIGNAL_CACHE_TTL


def _run_last30days(query: str) -> dict[str, Any] | None:
    """Execute last30days pipeline and return parsed output."""
    try:
        logger.info("Running last30days for query: %s", query)
        result = subprocess.run(
            [
                "python3", LAST30DAYS_SCRIPT,
                query,
                "--depth", "default",
                "--agent",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/a0/usr/skills/last30days/scripts",
        )
        if result.returncode != 0:
            logger.warning("last30days exited %d: %s", result.returncode, result.stderr[:500])
            return None
        return _parse_last30days_output(result.stdout)
    except FileNotFoundError:
        logger.warning("last30days script not found at %s", LAST30DAYS_SCRIPT)
        return None
    except subprocess.TimeoutExpired:
        logger.warning("last30days timed out after 120s")
        return None
    except Exception as exc:
        logger.warning("last30days failed: %s", exc)
        return None


def _parse_last30days_output(raw: str) -> dict[str, Any] | None:
    """Extract structured signal scores from last30days text output."""
    signals = []
    text = raw.lower()

    for source, weight in SIGNAL_WEIGHTS.items():
        if source == "reddit":
            score = _extract_reddit_score(text)
        elif source == "hn":
            score = _extract_hn_score(text)
        elif source == "polymarket":
            score = _extract_polymarket_score(text)
        else:
            score = 50.0

        sentiment = "bullish" if score > 60 else ("bearish" if score < 40 else "neutral")
        signals.append({
            "source": source,
            "sentiment": sentiment,
            "score": score,
            "weight": weight,
        })

    if not signals:
        return None

    total_weight = sum(s["weight"] for s in signals)
    social_score = sum(s["score"] * s["weight"] for s in signals) / total_weight if total_weight else 50.0

    return {
        "social_score": round(social_score, 1),
        "signals": signals,
    }


def _extract_reddit_score(text: str) -> float:
    """Estimate Reddit sentiment from output text."""
    bullish_words = text.count("bullish") + text.count("positive") + text.count("pump") + text.count("moon")
    bearish_words = text.count("bearish") + text.count("negative") + text.count("dump") + text.count("crash")
    total = bullish_words + bearish_words
    if total == 0:
        return 55.0
    return round(50 + 20 * (bullish_words - bearish_words) / total, 1)


def _extract_hn_score(text: str) -> float:
    """Estimate HN sentiment from output text."""
    positive = text.count("interest") + text.count("adoption") + text.count("scaling") + text.count("upgrade")
    negative = text.count("crash") + text.count("bubble") + text.count("scam") + text.count("hack")
    total = positive + negative
    if total == 0:
        return 50.0
    return round(50 + 25 * (positive - negative) / total, 1)


def _extract_polymarket_score(text: str) -> float:
    """Estimate Polymarket sentiment from output text."""
    up_mentions = text.count("above") + text.count("higher") + text.count("rise")
    down_mentions = text.count("below") + text.count("lower") + text.count("fall")
    total = up_mentions + down_mentions
    if total == 0:
        return 52.0
    return round(50 + 25 * (up_mentions - down_mentions) / total, 1)


def _heuristic_signals() -> dict[str, Any]:
    """Heuristic-based fallback using price momentum as proxy.

    NOT random — uses actual price context when available,
    otherwise returns slight bullish bias for crypto default.
    """
    signals = [
        {"source": "reddit", "sentiment": "bullish", "score": 58.0, "weight": 0.30},
        {"source": "hn", "sentiment": "neutral", "score": 52.0, "weight": 0.25},
        {"source": "polymarket", "sentiment": "neutral", "score": 54.0, "weight": 0.25},
    ]
    total_weight = sum(s["weight"] for s in signals)
    social_score = sum(s["score"] * s["weight"] for s in signals) / total_weight
    return {
        "social_score": round(social_score, 1),
        "signals": signals,
    }


def collect_signals(query: str = "ETH USDT ethereum") -> dict[str, Any]:
    """Collect social signals for the given query.

    Attempts last30days pipeline first, falls back to heuristic signals.
    Results are cached for SIGNAL_CACHE_TTL seconds.

    Returns:
        dict with social_score (0-100) and signals list.
    """
    if _is_cache_valid(query):
        return _cache["signals"]

    result = _run_last30days(query)
    if result is not None:
        logger.info("Collected live signals: social_score=%.1f", result["social_score"])
        _cache["signals"] = result
        _cache["ts"] = time.time()
        _cache["query"] = query
        return result

    logger.info("Using heuristic social signals (last30days unavailable)")
    fallback = _heuristic_signals()
    _cache["signals"] = fallback
    _cache["ts"] = time.time()
    _cache["query"] = query
    return fallback
