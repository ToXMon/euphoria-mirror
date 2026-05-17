"""Real ETH/USDT price data from Binance REST API.

Fetches OHLCV klines from Binance (no API key required).
Falls back to CoinGecko if Binance is geo-restricted (451).
Caches responses to avoid rate limiting.
"""

import logging
import time
from typing import Any

import pandas as pd
import requests

from backend.config import BINANCE_BASE_URL, CACHE_TTL, ETH_SYMBOL

logger = logging.getLogger(__name__)

# Alternative Binance endpoints
BINANCE_ENDPOINTS = [
    BINANCE_BASE_URL,
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Cache state
_cache: dict[str, Any] = {
    "ohlcv": None,
    "ohlcv_ts": 0.0,
    "ohlcv_key": None,
    "price": None,
    "price_ts": 0.0,
}


def _is_cache_valid(key: str, ttl: int | None = None) -> bool:
    """Check if cached data is still within TTL."""
    if ttl is None:
        ttl = CACHE_TTL
    ts_key = f"{key}_ts"
    if _cache.get(key) is None:
        return False
    return (time.time() - _cache.get(ts_key, 0.0)) < ttl


def _try_binance_klines(interval: str, limit: int) -> list | None:
    """Try multiple Binance endpoints for klines data."""
    params = {
        "symbol": ETH_SYMBOL,
        "interval": interval,
        "limit": min(limit, 1000),
    }
    for base_url in BINANCE_ENDPOINTS:
        url = f"{base_url}/api/v3/klines"
        try:
            logger.info("Trying Binance klines: %s", url)
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 451:
                logger.warning("Binance endpoint geo-restricted: %s", url)
                continue
            resp.raise_for_status()
            data = resp.json()
            if data:
                logger.info("Binance klines success from %s", url)
                return data
        except requests.exceptions.RequestException as exc:
            logger.warning("Binance endpoint %s failed: %s", url, exc)
            continue
    return None


def _try_binance_ticker() -> dict | None:
    """Try multiple Binance endpoints for 24hr ticker."""
    params = {"symbol": ETH_SYMBOL}
    for base_url in BINANCE_ENDPOINTS:
        url = f"{base_url}/api/v3/ticker/24hr"
        try:
            logger.info("Trying Binance ticker: %s", url)
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 451:
                logger.warning("Binance endpoint geo-restricted: %s", url)
                continue
            resp.raise_for_status()
            data = resp.json()
            if data:
                logger.info("Binance ticker success from %s", url)
                return data
        except requests.exceptions.RequestException as exc:
            logger.warning("Binance endpoint %s failed: %s", url, exc)
            continue
    return None


def _coingecko_price() -> dict[str, Any] | None:
    """Fetch current ETH price from CoinGecko as fallback."""
    url = f"{COINGECKO_BASE}/simple/price"
    params = {
        "ids": "ethereum",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_high_24hr": "true",
        "include_low_24hr": "true",
    }
    try:
        logger.info("Fetching ETH price from CoinGecko")
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        eth = data.get("ethereum", {})
        if not eth:
            return None
        return {
            "price": eth["usd"],
            "change_24h": eth.get("usd_24h_change", 0.0),
            "high_24h": eth.get("usd_24h_high", 0.0),
            "low_24h": eth.get("usd_24h_low", 0.0),
            "volume_24h": eth.get("usd_24h_vol", 0.0),
            "quote_volume_24h": eth.get("usd_24h_vol", 0.0),
        }
    except Exception as exc:
        logger.error("CoinGecko price failed: %s", exc)
        return None


def _coingecko_ohlcv(interval: str = "5m", limit: int = 500) -> pd.DataFrame | None:
    """Fetch OHLCV data from CoinGecko as fallback.

    CoinGecko OHLCV endpoint returns up to 30 days of data.
    Returns fewer data points but works globally.
    """
    url = f"{COINGECKO_BASE}/coins/ethereum/ohlc"
    params = {"vs_currency": "usd", "days": "1"}
    try:
        logger.info("Fetching ETH OHLCV from CoinGecko")
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        rows = []
        for k in data:
            # CoinGecko OHLC format: [timestamp, open, high, low, close]
            rows.append({
                "timestamp": pd.Timestamp(k[0], unit="ms", tz="UTC"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": 0.0,  # CoinGecko OHLC doesn't include volume
                "amount": 0.0,
            })
        df = pd.DataFrame(rows)
        df = df[["timestamp", "open", "high", "low", "close", "volume", "amount"]]
        logger.info("CoinGecko returned %d OHLCV candles", len(df))
        return df
    except Exception as exc:
        logger.error("CoinGecko OHLCV failed: %s", exc)
        return None


def _coingecko_market_chart(limit: int = 500) -> pd.DataFrame | None:
    """Fetch detailed price+volume data from CoinGecko market chart."""
    url = f"{COINGECKO_BASE}/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "1"}
    try:
        logger.info("Fetching ETH market chart from CoinGecko")
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        if not prices:
            return None

        # Build volume lookup by timestamp (rounded to nearest minute)
        vol_map = {}
        for ts, vol in volumes:
            key = int(ts // 60000) * 60000
            vol_map[key] = vol

        rows = []
        for i in range(len(prices)):
            ts_ms = prices[i][0]
            price = prices[i][1]
            vol_key = int(ts_ms // 60000) * 60000
            volume = vol_map.get(vol_key, 0.0)
            rows.append({
                "timestamp": pd.Timestamp(ts_ms, unit="ms", tz="UTC"),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
                "amount": volume * price,
            })

        df = pd.DataFrame(rows)
        df = df[["timestamp", "open", "high", "low", "close", "volume", "amount"]]

        # Resample to 5min OHLCV if we have enough points
        if len(df) > 20:
            df = df.set_index("timestamp")
            df = df.resample("5min").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "amount": "sum",
            }).dropna()
            df = df.reset_index()

        # Take last `limit` rows
        df = df.tail(limit).reset_index(drop=True)
        logger.info("CoinGecko market chart: %d candles", len(df))
        return df
    except Exception as exc:
        logger.error("CoinGecko market chart failed: %s", exc)
        return None


def get_ohlcv(interval: str = "5m", limit: int = 500) -> pd.DataFrame:
    """Fetch OHLCV klines. Tries Binance first, then CoinGecko."""
    cache_key = f"ohlcv_{interval}_{limit}"
    if _is_cache_valid("ohlcv") and _cache.get("ohlcv_key") == cache_key:
        return _cache["ohlcv"]

    # Try Binance first
    data = _try_binance_klines(interval, limit)
    if data is not None:
        rows = []
        for k in data:
            rows.append({
                "timestamp": pd.Timestamp(k[0], unit="ms", tz="UTC"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "amount": float(k[7]),  # quote asset volume
            })
        df = pd.DataFrame(rows)
        df = df[["timestamp", "open", "high", "low", "close", "volume", "amount"]]
        _cache["ohlcv"] = df
        _cache["ohlcv_ts"] = time.time()
        _cache["ohlcv_key"] = cache_key
        logger.info("Fetched %d klines from Binance", len(df))
        return df

    # Fallback to CoinGecko
    logger.info("Binance unavailable — falling back to CoinGecko")
    df = _coingecko_ohlcv(interval, limit)
    if df is not None and len(df) >= 10:
        _cache["ohlcv"] = df
        _cache["ohlcv_ts"] = time.time()
        _cache["ohlcv_key"] = cache_key
        return df

    # Final fallback: CoinGecko market chart
    df = _coingecko_market_chart(limit)
    if df is not None and len(df) >= 10:
        _cache["ohlcv"] = df
        _cache["ohlcv_ts"] = time.time()
        _cache["ohlcv_key"] = cache_key
        return df

    # Return stale cache if available
    if _cache["ohlcv"] is not None:
        logger.warning("All sources failed — returning stale cached OHLCV")
        return _cache["ohlcv"]

    raise RuntimeError("Failed to fetch OHLCV data from all sources (Binance + CoinGecko)")


def get_current_price() -> dict[str, Any]:
    """Get current ETH/USDT price. Tries Binance, then CoinGecko."""
    if _is_cache_valid("price"):
        return _cache["price"]

    # Try Binance first
    data = _try_binance_ticker()
    if data is not None:
        result = {
            "price": float(data["lastPrice"]),
            "change_24h": float(data["priceChangePercent"]),
            "high_24h": float(data["highPrice"]),
            "low_24h": float(data["lowPrice"]),
            "volume_24h": float(data["volume"]),
            "quote_volume_24h": float(data["quoteVolume"]),
        }
        _cache["price"] = result
        _cache["price_ts"] = time.time()
        logger.info("ETH/USDT from Binance: $%.2f (%.2f%% 24h)", result["price"], result["change_24h"])
        return result

    # Fallback to CoinGecko
    logger.info("Binance ticker unavailable — falling back to CoinGecko")
    result = _coingecko_price()
    if result is not None:
        _cache["price"] = result
        _cache["price_ts"] = time.time()
        logger.info("ETH/USDT from CoinGecko: $%.2f (%.2f%% 24h)", result["price"], result["change_24h"])
        return result

    # Return stale cache if available
    if _cache["price"] is not None:
        logger.warning("All price sources failed — returning stale cached price")
        return _cache["price"]

    raise RuntimeError("Failed to fetch ETH price from all sources (Binance + CoinGecko)")


def get_price_for_kronos(interval: str = "5m", limit: int = 500) -> pd.DataFrame:
    """Get OHLCV data formatted for Kronos prediction."""
    df = get_ohlcv(interval=interval, limit=limit)
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    return df
