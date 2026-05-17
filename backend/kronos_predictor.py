"""Production Kronos model wrapper for ETH/USDT price forecasting.

Loads the real Kronos model and tokenizer from HuggingFace Hub,
runs inference on OHLCV data, and returns structured predictions
for multiple time horizons.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.config import (
    GPU_ENABLED,
    KRONOS_MAX_CONTEXT,
    KRONOS_MODEL,
    KRONOS_SOURCE_PATH,
    KRONOS_TOKENIZER,
)

logger = logging.getLogger(__name__)

# Module-level state
_predictor: Any | None = None
_device: str = "cpu"
_model_loaded: bool = False
_load_error: str | None = None


def _detect_device() -> str:
    """Pick compute device: cuda > mps > cpu."""
    try:
        import torch
        if GPU_ENABLED and torch.cuda.is_available():
            logger.info("CUDA available — using GPU")
            return "cuda"
        if GPU_ENABLED and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("MPS available — using Apple Silicon GPU")
            return "mps"
    except ImportError:
        pass
    logger.info("No GPU detected — using CPU")
    return "cpu"


def _ensure_kronos_importable() -> None:
    """Add Kronos source directory to sys.path."""
    source = Path(KRONOS_SOURCE_PATH)
    if not source.exists():
        raise FileNotFoundError(
            f"Kronos source not found at {source}. "
            f"Clone the repo or set KRONOS_SOURCE_PATH env var."
        )
    source_str = str(source)
    if source_str not in sys.path:
        sys.path.insert(0, source_str)
        logger.info("Added %s to sys.path", source_str)


def load_model() -> bool:
    """Load Kronos model and tokenizer from HuggingFace Hub."""
    global _predictor, _device, _model_loaded, _load_error

    if _model_loaded and _predictor is not None:
        return True

    try:
        _ensure_kronos_importable()
        _device = _detect_device()

        import torch
        from model import Kronos, KronosPredictor, KronosTokenizer

        logger.info("Loading Kronos tokenizer from %s", KRONOS_TOKENIZER)
        tokenizer = KronosTokenizer.from_pretrained(KRONOS_TOKENIZER)

        logger.info("Loading Kronos model from %s on %s", KRONOS_MODEL, _device)
        model = Kronos.from_pretrained(KRONOS_MODEL)
        model.to(_device)
        model.eval()

        logger.info("Creating KronosPredictor with max_context=%d", KRONOS_MAX_CONTEXT)
        _predictor = KronosPredictor(model, tokenizer, max_context=KRONOS_MAX_CONTEXT)
        _model_loaded = True
        _load_error = None

        param_count = sum(p.numel() for p in model.parameters())
        logger.info("Kronos model loaded: %.1fM parameters on %s", param_count / 1e6, _device)
        return True

    except Exception as exc:
        _load_error = str(exc)
        _model_loaded = False
        _predictor = None
        logger.error("Failed to load Kronos model: %s", exc)
        return False


def is_model_loaded() -> bool:
    """Check if the Kronos model is loaded and ready."""
    return _model_loaded and _predictor is not None


def get_device() -> str:
    """Return the compute device string."""
    return _device


def get_load_error() -> str | None:
    """Return the last model loading error, if any."""
    return _load_error


def predict_eth(
    ohlcv_df: pd.DataFrame,
    pred_lengths: list[int] | None = None,
) -> dict[str, Any]:
    """Run Kronos prediction on OHLCV data for multiple horizons.

    Args:
        ohlcv_df: DataFrame with columns: open, high, low, close, volume, amount.
        pred_lengths: Prediction horizons in steps. Default: [1, 3, 12].

    Returns:
        Dict with forecast prices, direction, confidence, and raw predictions.
    """
    if pred_lengths is None:
        pred_lengths = [1, 3, 12]

    if not is_model_loaded():
        if not load_model():
            logger.warning("Model not available — returning heuristic fallback")
            return _heuristic_fallback(ohlcv_df)

    return _run_prediction(ohlcv_df, pred_lengths)


def _run_prediction(ohlcv_df: pd.DataFrame, pred_lengths: list[int]) -> dict[str, Any]:
    """Execute Kronos prediction pipeline."""
    df = ohlcv_df.copy()

    required = ["open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if "amount" not in df.columns:
        df["amount"] = df["volume"] * df["close"]

    if "timestamp" in df.columns:
        timestamps = pd.to_datetime(df["timestamp"])
    elif isinstance(df.index, pd.DatetimeIndex):
        timestamps = df.index.to_series()
    else:
        now = pd.Timestamp.utcnow()
        timestamps = pd.date_range(end=now, periods=len(df), freq="5min")

    lookback = min(400, len(df) - max(pred_lengths))
    if lookback < 50:
        logger.warning("Insufficient data for prediction: %d bars", len(df))
        return _heuristic_fallback(ohlcv_df)

    predictions = {}
    last_close = float(df["close"].iloc[-1])

    for pl in pred_lengths:
        try:
            last_ts = timestamps.iloc[-1]
            freq = pd.Timedelta(minutes=5)
            y_timestamp = pd.Series([last_ts + freq * (i + 1) for i in range(pl)])

            x_df = df.iloc[-lookback:][["open", "high", "low", "close", "volume", "amount"]].copy()
            x_timestamp = timestamps.iloc[-lookback:]

            pred_df = _predictor.predict(
                df=x_df.reset_index(drop=True),
                x_timestamp=x_timestamp.reset_index(drop=True),
                y_timestamp=y_timestamp,
                pred_len=pl,
                T=1.0,
                top_p=0.9,
                sample_count=1,
                verbose=False,
            )

            if isinstance(pred_df, pd.DataFrame) and "close" in pred_df.columns:
                pred_close = float(pred_df["close"].iloc[-1])
            else:
                pred_close = last_close

            horizon_label = _map_horizon(pl)
            predictions[horizon_label] = {
                "price": round(pred_close, 2),
                "change_pct": round((pred_close - last_close) / last_close * 100, 4),
                "direction": "up" if pred_close > last_close else ("down" if pred_close < last_close else "neutral"),
            }
            logger.info("Kronos %s: $%.2f (%.2f%%) %s", horizon_label, pred_close,
                         predictions[horizon_label]["change_pct"], predictions[horizon_label]["direction"])

        except Exception as exc:
            logger.error("Kronos prediction failed for horizon %d: %s", pl, exc)
            horizon_label = _map_horizon(pl)
            predictions[horizon_label] = {"price": last_close, "change_pct": 0.0, "direction": "neutral"}

    directions = [p["direction"] for p in predictions.values()]
    up_count = directions.count("up")
    down_count = directions.count("down")

    if up_count > down_count:
        overall_direction = "up"
    elif down_count > up_count:
        overall_direction = "down"
    else:
        overall_direction = "neutral"

    changes = [abs(p["change_pct"]) for p in predictions.values()]
    avg_change = sum(changes) / len(changes) if changes else 0
    agreement = max(up_count, down_count) / len(directions) if directions else 0
    confidence = min(0.95, 0.3 + agreement * 0.4 + min(avg_change / 2.0, 0.25))

    return {
        "forecast_5m": predictions.get("5m", {}).get("price", last_close),
        "forecast_15m": predictions.get("15m", {}).get("price", last_close),
        "forecast_1h": predictions.get("1h", {}).get("price", last_close),
        "direction": overall_direction,
        "model_confidence": round(confidence, 3),
        "predictions": predictions,
    }


def _map_horizon(steps: int) -> str:
    """Map step count to horizon label based on 5m bars."""
    if steps <= 1:
        return "5m"
    if steps <= 3:
        return "15m"
    return "1h"


def _heuristic_fallback(df: pd.DataFrame) -> dict[str, Any]:
    """Momentum-based fallback when Kronos model is unavailable.

    Uses SMA crossover + RSI as directional signal. NOT random.
    """
    closes = df["close"].values
    last_close = float(closes[-1])

    if len(closes) < 20:
        return {
            "forecast_5m": last_close, "forecast_15m": last_close, "forecast_1h": last_close,
            "direction": "neutral", "model_confidence": 0.1, "predictions": {},
        }

    sma5 = float(np.mean(closes[-5:]))
    sma20 = float(np.mean(closes[-20:]))
    momentum = (sma5 - sma20) / sma20

    deltas = np.diff(closes[-14:])
    gains = np.mean(deltas[deltas > 0]) if np.any(deltas > 0) else 0
    losses = -np.mean(deltas[deltas < 0]) if np.any(deltas < 0) else 0
    rs = gains / losses if losses > 0 else 100.0
    rsi = 100 - (100 / (1 + rs))

    if momentum > 0.002 and rsi > 55:
        direction = "up"
        bias = 0.001 + momentum * 0.5
    elif momentum < -0.002 and rsi < 45:
        direction = "down"
        bias = -0.001 + momentum * 0.5
    else:
        direction = "neutral"
        bias = momentum * 0.2

    conf = 0.3 + min(abs(momentum) * 50, 0.3)

    return {
        "forecast_5m": round(last_close * (1 + bias), 2),
        "forecast_15m": round(last_close * (1 + bias * 2), 2),
        "forecast_1h": round(last_close * (1 + bias * 4), 2),
        "direction": direction,
        "model_confidence": round(conf, 3),
        "predictions": {
            "5m": {"price": round(last_close * (1 + bias), 2), "change_pct": round(bias * 100, 4), "direction": direction},
            "15m": {"price": round(last_close * (1 + bias * 2), 2), "change_pct": round(bias * 200, 4), "direction": direction},
            "1h": {"price": round(last_close * (1 + bias * 4), 2), "change_pct": round(bias * 400, 4), "direction": direction},
        },
    }


def predict(ohlcv: list[list[float]]) -> dict[str, Any]:
    """Legacy predict interface accepting list-of-lists OHLCV.

    Args:
        ohlcv: list of [timestamp, open, high, low, close, volume]

    Returns:
        Dict with forecast_5m, forecast_15m, forecast_1h, confidence.
    """
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["amount"] = df["volume"] * df["close"]

    result = predict_eth(df)
    return {
        "forecast_5m": result["forecast_5m"],
        "forecast_15m": result["forecast_15m"],
        "forecast_1h": result["forecast_1h"],
        "confidence": result["model_confidence"],
    }
