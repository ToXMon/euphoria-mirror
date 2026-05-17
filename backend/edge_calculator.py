"""Edge Score fusion calculator.

Combines social signals, Kronos predictions, and price alignment
into a single 0-100 Edge Score with zone recommendations.
"""

from typing import Literal

from backend.config import EDGE_WEIGHTS


def _calculate_kronos_score(forecast: dict) -> float:
    """Convert Kronos forecast dict to a 0-100 directional score.

    Scores above 50 = bullish, below 50 = bearish.
    Based on predicted price change magnitude and confidence.
    """
    f5 = forecast.get("forecast_5m", 0)
    f15 = forecast.get("forecast_15m", 0)
    f1h = forecast.get("forecast_1h", 0)
    confidence = forecast.get("confidence", 0.5)

    if f5 == 0 and f15 == 0 and f1h == 0:
        return 50.0

    # Average predicted change vs current (5m as baseline)
    # Positive = bullish direction
    avg_forecast = (f5 + f15 + f1h) / 3
    baseline = f5 if f5 > 0 else avg_forecast
    if baseline == 0:
        return 50.0

    pct_change = ((avg_forecast - baseline) / baseline) * 100

    # Scale to 0-100, centered at 50
    # ±2% change maps to full range
    directional = 50 + (pct_change / 2.0) * 25
    directional = max(0, min(100, directional))

    # Weight by confidence
    score = 50 + (directional - 50) * confidence
    return round(max(0, min(100, score)), 1)


def _calculate_price_alignment(
    social_score: float,
    kronos_score: float,
) -> float:
    """How well social sentiment aligns with Kronos prediction direction.

    Returns 0-1 where 1 = perfect alignment.
    """
    social_dir = social_score - 50  # positive = bullish
    kronos_dir = kronos_score - 50

    if social_dir == 0 and kronos_dir == 0:
        return 0.5

    # Same direction = high alignment
    if (social_dir > 0 and kronos_dir > 0) or (social_dir < 0 and kronos_dir < 0):
        # Scale by magnitude agreement
        max_mag = max(abs(social_dir), abs(kronos_dir), 1)
        alignment = 0.5 + 0.5 * min(abs(social_dir), abs(kronos_dir)) / max_mag
    else:
        # Opposing directions
        alignment = 0.5 - 0.3 * min(abs(social_dir), abs(kronos_dir)) / 50

    return round(max(0, min(1, alignment)), 3)


def _get_confidence_level(edge_score: float, agreement: float) -> Literal["high", "medium", "low"]:
    """Determine confidence level based on edge score and signal agreement."""
    if edge_score > 70 and agreement > 0.7:
        return "high"
    if edge_score > 55 or agreement > 0.6:
        return "medium"
    return "low"


def _get_zone_recommendation(
    edge_score: float,
    kronos_score: float,
    social_score: float,
) -> str:
    """Map edge score to euphoria zone recommendation.

    Zones represent price ranges. Recommend the zone most likely to hit
    based on predicted direction and magnitude.
    """
    direction = "up" if kronos_score > 50 else "down"
    magnitude = abs(edge_score - 50)

    if direction == "up":
        if edge_score > 75:
            return "Zone +3 (aggressive bullish: +1.5% to +2.0%)"
        if edge_score > 65:
            return "Zone +2 (moderate bullish: +0.8% to +1.5%)"
        if edge_score > 55:
            return "Zone +1 (slight bullish: +0.2% to +0.8%)"
        return "Neutral zone (flat: -0.2% to +0.2%)"
    else:
        if edge_score < 25:
            return "Zone -3 (aggressive bearish: -1.5% to -2.0%)"
        if edge_score < 35:
            return "Zone -2 (moderate bearish: -0.8% to -1.5%)"
        if edge_score < 45:
            return "Zone -1 (slight bearish: -0.2% to -0.8%)"
        return "Neutral zone (flat: -0.2% to +0.2%)"


def calculate_edge(
    social_score: float,
    kronos_forecast: dict,
) -> dict:
    """Calculate the combined Edge Score.

    Edge Score = W_social * social_score + W_kronos * kronos_score
                 + W_alignment * price_alignment * 100

    Args:
        social_score: Aggregated social signal score (0-100)
        kronos_forecast: Dict with forecast_5m, forecast_15m, forecast_1h, confidence

    Returns:
        Dict with edge_score, confidence, zone_recommendation, kronos_score, price_alignment
    """
    kronos_score = _calculate_kronos_score(kronos_forecast)
    price_alignment = _calculate_price_alignment(social_score, kronos_score)

    edge_score = (
        EDGE_WEIGHTS["social"] * social_score
        + EDGE_WEIGHTS["kronos"] * kronos_score
        + EDGE_WEIGHTS["price_alignment"] * price_alignment * 100
    )
    edge_score = round(max(0, min(100, edge_score)), 1)

    confidence = _get_confidence_level(edge_score, price_alignment)
    zone = _get_zone_recommendation(edge_score, kronos_score, social_score)

    return {
        "edge_score": edge_score,
        "confidence": confidence,
        "zone_recommendation": zone,
        "kronos_score": kronos_score,
        "price_alignment": price_alignment,
    }
