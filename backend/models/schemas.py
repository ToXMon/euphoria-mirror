"""Pydantic models for Kronos backend API."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SignalBreakdown(BaseModel):
    source: str = Field(description="Signal source name")
    sentiment: Literal["bullish", "bearish", "neutral"] = Field(description="Sentiment direction")
    score: float = Field(ge=0, le=100, description="Signal score 0-100")
    weight: float = Field(ge=0, le=1, description="Weight in fusion formula")


class KronosForecast(BaseModel):
    forecast_5m: float = Field(description="5-minute price forecast (USD)")
    forecast_15m: float = Field(description="15-minute price forecast (USD)")
    forecast_1h: float = Field(description="1-hour price forecast (USD)")
    confidence: float = Field(ge=0, le=1, description="Model confidence 0-1")


class ForecastDetail(BaseModel):
    price: float = Field(description="Predicted price")
    direction: Literal["up", "down", "neutral"] = Field(description="Predicted direction")
    change_pct: float = Field(description="Predicted percentage change")
    confidence: float = Field(ge=0, le=1, description="Forecast confidence")


class ZoneInfo(BaseModel):
    price_low: float = Field(description="Zone lower price bound")
    price_high: float = Field(description="Zone upper price bound")
    direction: Literal["up", "down"] = Field(description="Zone direction from current price")
    edge_score: float = Field(ge=0, le=100, description="Edge score for this zone")
    label: Literal["recommended", "caution", "avoid"] = Field(description="Zone recommendation label")


class PredictionResponse(BaseModel):
    edge_score: float = Field(ge=0, le=100, description="Combined edge score 0-100")
    confidence: Literal["high", "medium", "low"] = Field(description="Overall confidence level")
    current_price: float = Field(description="Current ETH/USDT price")
    price_change_24h: float = Field(description="24h price change percentage")
    kronos_forecast: KronosForecast = Field(description="Kronos price forecasts")
    forecast_details: dict = Field(description="Detailed forecasts per horizon")
    social_score: float = Field(ge=0, le=100, description="Aggregated social score")
    social_signals: List[SignalBreakdown] = Field(description="Individual signal breakdowns")
    zones: List[ZoneInfo] = Field(description="Zone grid with 10 zones")
    zone_recommendation: str = Field(description="Which zone to bet on")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Prediction timestamp")


class SignalsResponse(BaseModel):
    social_score: float = Field(ge=0, le=100)
    signals: List[SignalBreakdown]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PriceResponse(BaseModel):
    symbol: str = Field(description="Trading pair symbol")
    price: float = Field(description="Current price")
    change_24h: float = Field(description="24h price change percentage")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BacktestRequest(BaseModel):
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")
    initial_balance: float = Field(default=10000.0, gt=0, description="Starting balance in USD")


class BacktestTrade(BaseModel):
    entry_time: str = Field(description="Trade entry timestamp")
    exit_time: str = Field(description="Trade exit timestamp")
    direction: Literal["long", "short"] = Field(description="Trade direction")
    entry_price: float = Field(description="Entry price")
    exit_price: float = Field(description="Exit price")
    pnl: float = Field(description="Profit/loss in USD")
    pnl_pct: float = Field(description="Profit/loss percentage")
    edge_score_at_entry: float = Field(description="Edge score when trade was opened")


class BacktestResponse(BaseModel):
    total_trades: int = Field(ge=0)
    win_rate: float = Field(ge=0, le=1, description="Win rate 0-1")
    pnl: float = Field(description="Total profit/loss in USD")
    max_drawdown: float = Field(description="Max drawdown percentage")
    sharpe_ratio: float = Field(description="Annualized Sharpe ratio")
    trades: List[BacktestTrade] = Field(description="Individual trade records")


class HealthResponse(BaseModel):
    status: str = Field(description="Service status")
    model_loaded: bool = Field(description="Whether Kronos model is loaded")
    device: str = Field(description="Compute device (cpu/cuda/mps)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
