"""Kronos Euphoria Trading Edge Prediction Mirror — Production FastAPI backend.

Endpoints:
    GET  /health            — health check with model status
    GET  /api/v1/prediction — Full prediction pipeline
    GET  /api/v1/price      — Current ETH/USDT price
    GET  /api/v1/signals    — Social signal breakdown
    POST /api/v1/backtest   — Run backtest on historical data
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import ALIGNMENT_WEIGHT, CORS_ORIGINS, EDGE_WEIGHTS, KRONOS_WEIGHT, SOCIAL_WEIGHT
from backend.kronos_predictor import (
    get_device,
    get_load_error,
    is_model_loaded,
    load_model,
    predict_eth,
)
from backend.models.schemas import (
    BacktestRequest,
    BacktestResponse,
    BacktestTrade,
    HealthResponse,
    KronosForecast,
    PredictionResponse,
    PriceResponse,
    SignalBreakdown,
    SignalsResponse,
    ZoneInfo,
)
from backend.price_fetcher import get_current_price, get_price_for_kronos
from backend.signal_collector import collect_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("kronos-backend")

app = FastAPI(
    title="Kronos Euphoria Trading Edge",
    version="1.0.0",
    description="Production prediction mirror for ETH/USDT with Kronos model inference",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"


@app.on_event("startup")
async def startup_event() -> None:
    """Preload Kronos model on startup."""
    logger.info("Preloading Kronos model...")
    success = load_model()
    if success:
        logger.info("Kronos model preloaded on %s", get_device())
    else:
        logger.warning("Kronos model preload failed: %s — will use heuristic fallback", get_load_error())


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=is_model_loaded(),
        device=get_device(),
        timestamp=datetime.utcnow(),
    )


@app.get("/api/v1/price", response_model=PriceResponse)
def get_price() -> PriceResponse:
    """Current ETH/USDT price from Binance."""
    try:
        data = get_current_price()
        return PriceResponse(
            symbol="ETHUSDT",
            price=data["price"],
            change_24h=data["change_24h"],
            timestamp=datetime.utcnow(),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Price fetch failed: {exc}") from exc


@app.get("/api/v1/signals", response_model=SignalsResponse)
def get_signals() -> SignalsResponse:
    """Social signal breakdown from last30days pipeline."""
    signal_data = collect_signals()
    signals = [SignalBreakdown(**s) for s in signal_data["signals"]]
    return SignalsResponse(
        social_score=signal_data["social_score"],
        signals=signals,
        timestamp=datetime.utcnow(),
    )


def _calculate_kronos_score(forecast: dict) -> float:
    """Convert Kronos forecast to 0-100 directional score."""
    f5 = forecast.get("forecast_5m", 0)
    f15 = forecast.get("forecast_15m", 0)
    f1h = forecast.get("forecast_1h", 0)
    confidence = forecast.get("confidence", 0.5)

    if f5 == 0 and f15 == 0 and f1h == 0:
        return 50.0

    avg_forecast = (f5 + f15 + f1h) / 3
    baseline = f5 if f5 > 0 else avg_forecast
    if baseline == 0:
        return 50.0

    pct_change = ((avg_forecast - baseline) / baseline) * 100
    directional = 50 + (pct_change / 2.0) * 25
    directional = max(0, min(100, directional))
    score = 50 + (directional - 50) * confidence
    return round(max(0, min(100, score)), 1)


def _calculate_alignment(social_score: float, kronos_score: float) -> float:
    """Signal alignment 0-1."""
    social_dir = social_score - 50
    kronos_dir = kronos_score - 50
    if social_dir == 0 and kronos_dir == 0:
        return 0.5
    if (social_dir > 0 and kronos_dir > 0) or (social_dir < 0 and kronos_dir < 0):
        max_mag = max(abs(social_dir), abs(kronos_dir), 1)
        return 0.5 + 0.5 * min(abs(social_dir), abs(kronos_dir)) / max_mag
    return max(0.0, 0.5 - 0.3 * min(abs(social_dir), abs(kronos_dir)) / 50)


def _confidence_level(edge_score: float, alignment: float) -> str:
    if edge_score > 70 and alignment > 0.7:
        return "high"
    if edge_score > 55 or alignment > 0.6:
        return "medium"
    return "low"


def _calculate_zones(current_price: float, edge_score: float, direction: str) -> list[ZoneInfo]:
    """Generate 10 price zones: 5 above, 5 below current price.

    Each zone is 1% wide. Zones are labeled based on edge score
    and distance from the predicted direction.
    """
    zones = []
    zone_width_pct = 0.01  # 1% per zone

    for i in range(1, 6):
        # Zones above current price
        low_up = current_price * (1 + zone_width_pct * (i - 1))
        high_up = current_price * (1 + zone_width_pct * i)
        # Edge decays with distance from current price
        zone_edge_up = max(0, edge_score - (i - 1) * 5)
        # Label: if direction is up, close zones are recommended
        if direction == "up":
            label_up = "recommended" if i <= 2 else ("caution" if i <= 4 else "avoid")
        else:
            label_up = "avoid" if i <= 2 else "caution"
        zones.append(ZoneInfo(
            price_low=round(low_up, 2),
            price_high=round(high_up, 2),
            direction="up",
            edge_score=round(zone_edge_up, 1),
            label=label_up,
        ))

        # Zones below current price
        low_down = current_price * (1 - zone_width_pct * i)
        high_down = current_price * (1 - zone_width_pct * (i - 1))
        zone_edge_down = max(0, 100 - edge_score - (i - 1) * 5)
        if direction == "down":
            label_down = "recommended" if i <= 2 else ("caution" if i <= 4 else "avoid")
        else:
            label_down = "avoid" if i <= 2 else "caution"
        zones.append(ZoneInfo(
            price_low=round(low_down, 2),
            price_high=round(high_down, 2),
            direction="down",
            edge_score=round(zone_edge_down, 1),
            label=label_down,
        ))

    # Sort: above zones first (by price ascending), then below (by price descending)
    above = sorted([z for z in zones if z.direction == "up"], key=lambda z: z.price_low)
    below = sorted([z for z in zones if z.direction == "down"], key=lambda z: z.price_low, reverse=True)
    return above + below


def _zone_recommendation(edge_score: float, direction: str) -> str:
    """Map edge score to zone recommendation text."""
    if direction == "up":
        if edge_score > 75:
            return "Zone +2 to +3 (strong bullish: +1% to +2%)"
        if edge_score > 65:
            return "Zone +1 to +2 (moderate bullish: +0.5% to +1.5%)"
        if edge_score > 55:
            return "Zone +1 (slight bullish: +0.2% to +0.8%)"
        return "Neutral zone — no clear edge"
    if direction == "down":
        if edge_score < 25:
            return "Zone -2 to -3 (strong bearish: -1% to -2%)"
        if edge_score < 35:
            return "Zone -1 to -2 (moderate bearish: -0.5% to -1.5%)"
        if edge_score < 45:
            return "Zone -1 (slight bearish: -0.2% to -0.8%)"
        return "Neutral zone — no clear edge"
    return "Neutral zone — flat prediction"


@app.get("/api/v1/prediction", response_model=PredictionResponse)
def get_prediction() -> PredictionResponse:
    """Full prediction pipeline: Binance data -> Kronos forecast -> Social signals -> Edge Score."""
    logger.info("Prediction requested")

    # Step 1: Fetch real ETH/USDT data from Binance
    try:
        price_data = get_current_price()
        ohlcv_df = get_price_for_kronos(interval="5m", limit=500)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Data fetch failed: {exc}") from exc

    current_price = price_data["price"]
    change_24h = price_data["change_24h"]

    if len(ohlcv_df) < 50:
        raise HTTPException(status_code=503, detail="Insufficient OHLCV data from Binance")

    # Step 2: Run Kronos prediction
    kronos_result = predict_eth(ohlcv_df, pred_lengths=[1, 3, 12])

    # Step 3: Collect social signals
    signal_data = collect_signals()
    social_score = signal_data["social_score"]
    signals = [SignalBreakdown(**s) for s in signal_data["signals"]]

    # Step 4: Calculate Edge Score
    kronos_score = _calculate_kronos_score(kronos_result)
    alignment = _calculate_alignment(social_score, kronos_score)

    edge_score = (
        EDGE_WEIGHTS["social"] * social_score
        + EDGE_WEIGHTS["kronos"] * kronos_score
        + EDGE_WEIGHTS["price_alignment"] * alignment * 100
    )
    edge_score = round(max(0, min(100, edge_score)), 1)

    confidence = _confidence_level(edge_score, alignment)
    direction = kronos_result.get("direction", "neutral")

    # Step 5: Build zone grid
    zones = _calculate_zones(current_price, edge_score, direction)
    zone_rec = _zone_recommendation(edge_score, direction)

    # Build forecast details
    forecast_details = {}
    for horizon, data in kronos_result.get("predictions", {}).items():
        forecast_details[horizon] = {
            "price": data.get("price", current_price),
            "direction": data.get("direction", "neutral"),
            "change_pct": data.get("change_pct", 0.0),
            "confidence": kronos_result.get("model_confidence", 0.5),
        }

    return PredictionResponse(
        edge_score=edge_score,
        confidence=confidence,
        current_price=current_price,
        price_change_24h=change_24h,
        kronos_forecast=KronosForecast(
            forecast_5m=kronos_result["forecast_5m"],
            forecast_15m=kronos_result["forecast_15m"],
            forecast_1h=kronos_result["forecast_1h"],
            confidence=kronos_result.get("model_confidence", 0.5),
        ),
        forecast_details=forecast_details,
        social_score=social_score,
        social_signals=signals,
        zones=zones,
        zone_recommendation=zone_rec,
        timestamp=datetime.utcnow(),
    )


@app.post("/api/v1/backtest", response_model=BacktestResponse)
def run_backtest(req: BacktestRequest) -> BacktestResponse:
    """Run backtest simulation over historical data from Binance."""
    logger.info("Backtest requested: %s to %s", req.start_date, req.end_date)

    try:
        start_dt = datetime.strptime(req.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(req.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Fetch enough historical data
    days = (end_dt - start_dt).days
    if days <= 0 or days > 30:
        raise HTTPException(status_code=400, detail="Date range must be 1-30 days.")

    try:
        # Fetch 1h klines to cover the date range
        limit = min(days * 24 + 100, 1000)
        ohlcv_df = get_price_for_kronos(interval="1h", limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to fetch historical data: {exc}") from exc

    if len(ohlcv_df) < 24:
        raise HTTPException(status_code=400, detail="Insufficient data for backtest")

    # Simple edge-gated backtest
    balance = req.initial_balance
    peak_balance = balance
    max_drawdown = 0.0
    trades: list[BacktestTrade] = []
    position: dict | None = None
    returns: list[float] = []

    closes = ohlcv_df["close"].values
    timestamps = ohlcv_df["timestamp"].values if "timestamp" in ohlcv_df.columns else range(len(closes))

    window_size = 24
    for i in range(window_size, len(closes)):
        window_closes = closes[max(0, i - window_size):i]
        current_close = float(closes[i])
        ts_str = str(timestamps[i]) if i < len(timestamps) else f"bar_{i}"

        # Mini prediction on window
        window_df = ohlcv_df.iloc[max(0, i - window_size):i].copy()
        kronos_result = predict_eth(window_df, pred_lengths=[1])
        social_score = 55.0  # simplified for backtest
        kronos_score = _calculate_kronos_score(kronos_result)
        alignment = _calculate_alignment(social_score, kronos_score)
        edge = (
            EDGE_WEIGHTS["social"] * social_score
            + EDGE_WEIGHTS["kronos"] * kronos_score
            + EDGE_WEIGHTS["price_alignment"] * alignment * 100
        )
        edge = max(0, min(100, edge))

        # Position management
        if position is not None:
            should_close = (
                (position["direction"] == "long" and edge < 45)
                or (position["direction"] == "short" and edge > 55)
                or i == len(closes) - 1
            )
            if should_close:
                exit_price = current_close
                if position["direction"] == "long":
                    pnl = (exit_price - position["entry_price"]) / position["entry_price"] * balance * 0.1
                else:
                    pnl = (position["entry_price"] - exit_price) / position["entry_price"] * balance * 0.1
                pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"] * 100
                if position["direction"] == "short":
                    pnl_pct = -pnl_pct
                balance += pnl
                returns.append(pnl / (balance - pnl) if (balance - pnl) > 0 else 0)
                trades.append(BacktestTrade(
                    entry_time=position["entry_time"],
                    exit_time=ts_str,
                    direction=position["direction"],
                    entry_price=round(position["entry_price"], 2),
                    exit_price=round(exit_price, 2),
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 2),
                    edge_score_at_entry=round(position["edge_at_entry"], 1),
                ))
                peak_balance = max(peak_balance, balance)
                drawdown = (peak_balance - balance) / peak_balance * 100
                max_drawdown = max(max_drawdown, drawdown)
                position = None

        if position is None:
            if edge > 65:
                position = {
                    "direction": "long",
                    "entry_price": current_close,
                    "entry_time": ts_str,
                    "edge_at_entry": edge,
                }
            elif edge < 35:
                position = {
                    "direction": "short",
                    "entry_price": current_close,
                    "entry_time": ts_str,
                    "edge_at_entry": edge,
                }

    # Calculate stats
    total_pnl = balance - req.initial_balance
    wins = [t for t in trades if t.pnl > 0]
    win_rate = len(wins) / len(trades) if trades else 0.0

    avg_return = sum(returns) / len(returns) if returns else 0.0
    std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if len(returns) > 1 else 1.0
    sharpe = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0.0

    return BacktestResponse(
        total_trades=len(trades),
        win_rate=round(win_rate, 3),
        pnl=round(total_pnl, 2),
        max_drawdown=round(max_drawdown, 2),
        sharpe_ratio=round(sharpe, 2),
        trades=trades,
    )


# Serve dashboard static files at root
if DASHBOARD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")
