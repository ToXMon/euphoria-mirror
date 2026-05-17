# SPEC: Kronos Euphoria Trading Edge — Prediction Mirror

## Objective

Build a standalone web dashboard that gives prediction-game players real-time analytical edge by fusing **Kronos candlestick forecasting** with **last30days social signal intelligence**, displayed as an overlay on the euphoria.finance zone grid.

**Key constraint**: euphoria.finance has NO public API — it is a game/simulation where users tap price zones. We build a standalone "Prediction Mirror" that mimics the euphoria grid interface and overlays Kronos predictions.

### User Stories

| As a... | I want... | So that... |
|---------|-----------|------------|
| Solo trader | View ETH/USDT Edge Score before each euphoria trade | I can validate my intuition against social sentiment + model forecast |
| New user | Open the dashboard and immediately understand zones to tap | I learn faster and feel more confident |
| Analyst | See the breakdown of which signals contributed to the Edge Score | I can trust the system and debug false positives |

### Success Criteria

- Dashboard loads in < 3s on desktop
- Edge Score (0-100) updates every 60 seconds
- Kronos ETH/USDT forecast covers 5-minute, 15-minute, 1-hour horizons
- last30days signals: Reddit, HackerNews, Polymarket, GitHub (zero-config sources)
- Akash GPU deployment (A10G or T4) for inference
- Standalone HTML dashboard — no browser extension required

---

## ASSUMPTIONS I'M MAKING

1. **ETH-only**: euphoria.finance is ETH-only → single ETH/USDT prediction stream
2. **GPU deployment**: User prefers GPU (A10G ~$100-150/mo or T4 ~$50-80/mo on Akash)
3. **60s refresh**: Pre-trade analysis (1-2 min before trade window) is sufficient latency
4. **Social signals only for MVP**: NO macro events, geopolitical, or on-chain whale tracking
5. **Standalone dashboard**: NOT a browser extension — self-contained HTML
6. **Kronos-mini on GPU**: 4.1M params, fast inference, sufficient for MVP
7. **last30days zero-config**: Reddit, HN, Polymarket, YouTube work without API keys

→ **Correct me now or I'll proceed with these.**

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Inference** | Kronos-mini | NeoQuasar/Kronos-mini | ETH/USDT candlestick forecasting |
| **Social signals** | last30days | skill v3 | 14+ platform social sentiment |
| **GPU runtime** | Akash Network | mainnet-17 | GPU deployment (A10G/T4) |
| **Dashboard** | Vanilla HTML/JS | ES2022 | Standalone, no build step |
| **Backend API** | FastAPI | 0.110+ | Inference endpoint + signal aggregation |
| **Data fetching** | crypto_price MCP | Alchemy | Real-time ETH/USDT price |

---

## Commands

### Development

```bash
# Start inference API locally
cd kronos-euphoria-backend && uvicorn main:app --reload --port 8000

# Run last30days social signal extraction
cd /a0/usr/skills/last30days/scripts && python3 last30days.py "ETH USDT" --depth default --agent

# Serve dashboard locally
python3 -m http.server 8080 --directory dashboard
```

### Akash Deployment

```bash
# Deploy GPU inference service
provider-services tx deployment create akash-sdl.yaml --dseq $DSEQ --from $WALLET

# Send manifest
provider-services send-manifest akash-sdl.yaml --dseq $DSEQ --provider $PROVIDER --from $WALLET

# Close deployment
provider-services tx deployment close --dseq $DSEQ --from $WALLET
```

### Testing

```bash
# Run inference tests
pytest tests/test_inference.py -v

# Run signal fusion tests
pytest tests/test_signal_fusion.py -v

# Run dashboard e2e
playwright test tests/dashboard.spec.ts
```

---

## Project Structure

```
kronos-euphoria-trading-edge/
├── SPEC.md                           # This specification
├── dashboard/                        # Standalone HTML dashboard
│   ├── index.html                   # Main dashboard (euphoria mirror)
│   ├── css/
│   │   └── dashboard.css             # Zone grid + prediction overlay styles
│   ├── js/
│   │   ├── app.js                    # Main dashboard logic
│   │   ├── api.js                    # Backend API client
│   │   ├── edge-score.js            # Edge Score calculation
│   │   ├── zone-grid.js             # Euphoria-style zone renderer
│   │   └── signals.js               # last30days signal display
│   └── assets/
│       └── favicon.svg
├── backend/                          # FastAPI inference service
│   ├── main.py                       # FastAPI app entry
│   ├── kronos_predictor.py           # Kronos-mini wrapper
│   ├── signal_collector.py           # last30days integration
│   ├── edge_calculator.py             # Edge Score fusion logic
│   ├── price_fetcher.py              # ETH/USDT price from Alchemy
│   ├── models/
│   │   └── schemas.py               # Pydantic request/response models
│   └── config.py                    # Environment config
├── akash/                           # Akash deployment files
│   ├── sdl/
│   │   └── gpu-inference.yaml       # A10G GPU SDL (~$100-150/mo)
│   └── scripts/
│       ├── deploy.sh                # Deployment automation
│       └── update.sh                # Rolling update script
├── tests/
│   ├── test_inference.py            # Kronos inference unit tests
│   ├── test_signal_fusion.py        # Edge Score calculation tests
│   ├── test_api.py                  # API endpoint tests
│   └── dashboard/
│       └── dashboard.spec.ts        # Playwright e2e tests
├── data/
│   └── sample_eth_ohlcv.csv          # Sample ETH/USDT OHLCV for testing
└── README.md
```

---

## Code Style

### Python Backend (FastAPI)

```python
# Example: Edge Score calculation
from dataclasses import dataclass

@dataclass
class EdgeComponents:
    social_score: float      # 0-100 from last30days
    kronos_score: float    # 0-100 from Kronos forecast confidence
    price_alignment: float  # 0-1 how well signals align with current price

def calculate_edge_score(components: EdgeComponents) -> dict:
    """
    Fusion formula: weighted combination of signal sources.
    Edge Score = 0.50 × social + 0.35 × kronos + 0.15 × alignment
    """
    edge = (
        0.50 * components.social_score +
        0.35 * components.kronos_score +
        0.15 * components.price_alignment * 100
    )
    return {
        "edge_score": round(min(100, max(0, edge)), 1),
        "confidence": "high" if edge >= 70 else "medium" if edge >= 40 else "low",
        "zone_recommendation": get_zone(edge)
    }
```

### TypeScript Dashboard (Vanilla JS)

```typescript
// Example: Zone grid renderer
interface ZonePrediction {
  zonePrice: number;       // Center price of zone
  edgeScore: number;       // 0-100
  direction: 'up' | 'down' | 'neutral';
  signals: SignalBreakdown;
}

function renderZoneGrid(zones: ZonePrediction[], container: HTMLElement): void {
  const grid = document.createElement('div');
  grid.className = 'zone-grid';
  
  zones.forEach(zone => {
    const cell = document.createElement('div');
    cell.className = `zone zone--${zone.direction}`;
    cell.innerHTML = `
      <span class="zone-price">${zone.zonePrice.toFixed(2)}</span>
      <span class="zone-edge" data-score="${zone.edgeScore}">${zone.edgeScore}</span>
      <span class="zone-signals">${zone.signals.count} signals</span>
    `;
    grid.appendChild(cell);
  });
  
  container.appendChild(grid);
}
```

**Naming conventions:**
- Variables: `camelCase` for JS, `snake_case` for Python
- Functions: `verbNoun` pattern (e.g., `calculateEdgeScore`, `fetch_price`)
- Constants: `SCREAMING_SNAKE_CASE`
- CSS classes: `kebab-case` with BEM-like suffixes (e.g., `zone-grid__cell--highlighted`)

---

## Testing Strategy

### Test Levels

| Level | Scope | Tools | Coverage Target |
|-------|-------|-------|------------------|
| **Unit** | Kronos inference, Edge Score calculation, signal fusion | pytest | 80%+ |
| **Integration** | API endpoints, signal collection pipeline | pytest + httpx | 70%+ |
| **E2E** | Dashboard render, zone overlay, refresh cycle | Playwright | Happy path + edge cases |

### Test Locations

```
tests/
├── unit/
│   ├── test_edge_calculator.py
│   ├── test_kronos_predictor.py
│   └── test_signal_normalizer.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_signal_collector.py
└── e2e/
    └── test_dashboard_flow.py
```

### Acceptance Tests (from Success Criteria)

```python
def test_edge_score_updates_every_60_seconds():
    """Dashboard refreshes Edge Score every 60s without page reload."""
    # Load dashboard, capture initial score, wait 65s, verify updated

def test_kronos_eth_forecast_covers_three_horizons():
    """API returns 5m, 15m, 1h ETH/USDT forecasts."""
    response = client.get("/predict?pair=ETHUSDT")
    assert set(response.json()['horizons']) == {'5m', '15m', '1h'}

def test_social_signals_from_four_sources():
    """Edge Score includes Reddit, HN, Polymarket, YouTube signals."""
    response = client.get("/signals?pair=ETHUSDT")
    sources = response.json()['signals_by_source'].keys()
    assert {'reddit', 'hackernews', 'polymarket', 'youtube'}.issubset(sources)
```

---

## Boundaries

### Always Do

- Run `pytest tests/` before any commit
- Validate inputs at API boundary (price range, pair format)
- Log all inference requests with latency metadata
- Keep API keys in environment variables, never in source

### Ask First

- Adding new signal sources beyond last30days (changes Edge Score weight)
- Modifying GPU instance type (changes Akash cost)
- Adding new prediction horizons (changes Kronos lookback)
- Changing dashboard color scheme (changes user experience)

### Never Do

- Commit secrets or API keys to source control
- Remove failing tests without approval
- Deploy to production without human gate approval
- Make real trades — this is a demonstration tool, not a trading bot

---

## Functional Requirements

### FR-1: Prediction Mirror Dashboard

The dashboard mimics the euphoria.finance zone grid interface:

1. **Zone Grid**: 10-20 price zones covering the current ETH/USDT trading range
2. **Zone Width**: Each zone spans 0.5% price range (configurable)
3. **User Position**: Marked zones that user has placed predictions on
4. **Prediction Overlay**: Kronos forecast + Edge Score displayed per zone

**Zone grid layout (ASCII representation):**

```
+----------+----------+----------+----------+
| Zone 1   | Zone 2   | Zone 3   | Zone 4   |  ← Lower price
| Edge: 45 | Edge: 72 | Edge: 38 | Edge: 61 |
| ↑ 2 sig  | ↑ 5 sig  | ↓ 1 sig  | ↑ 4 sig  |
+----------+----------+----------+----------+
| Zone 5   | Zone 6   | Zone 7   | Zone 8   |
| Edge: 55 | Edge: 83 | Edge: 29 | Edge: 67 |
| ↑ 3 sig  | ↑ 6 sig  | ↓ 2 sig  | ↑ 3 sig  |
+----------+----------+----------+----------+
| Zone 9   | Zone 10  | [MORE]   |          |  ← Higher price
+----------+----------+----------+----------+
```

### FR-2: Edge Score Calculation

**Formula:**

```
Edge Score = (0.50 × Social_Score) + (0.35 × Kronos_Score) + (0.15 × Price_Alignment)

Where:
  Social_Score    = last30days composite signal (0-100)
  Kronos_Score    = Kronos forecast confidence × directional agreement (0-100)
  Price_Alignment = how well social signals predict current price movement (0-1)
```

**Signal weights for MVP:**

| Source | Weight | Data |
|--------|--------|------|
| Reddit | 0.30 | Upvote velocity on ETH posts |
| HackerNews | 0.25 | Tech sentiment correlation |
| Polymarket | 0.25 | Real-money prediction odds |
| YouTube | 0.20 | Creator sentiment breakdown |

### FR-3: Kronos ETH/USDT Forecasting

**Model**: Kronos-mini (4.1M params, HuggingFace: `NeoQuasar/Kronos-mini`)

**Input**: Recent ETH/USDT OHLCV candlesticks (lookback: 200 candles)

**Output per horizon**:

```json
{
  "pair": "ETHUSDT",
  "horizon": "5m",
  "forecast": {
    "direction": "up",
    "bias": 0.62,
    "range_low": 3245.50,
    "range_high": 3268.20,
    "confidence": 0.78
  },
  "metadata": {
    "model_version": "Kronos-mini-v1",
    "inference_latency_ms": 142
  }
}
```

**Supported horizons**: 5m, 15m, 1h

### FR-4: Social Signal Collection

**last30days integration** (zero-config sources):

| Source | Endpoint | Refresh |
|--------|----------|---------|
| Reddit | Public JSON (r/ethfinance, r/ethereum) | 60s |
| HackerNews | Algolia API | 60s |
| Polymarket | Gamma API | 60s |
| YouTube | yt-dlp transcript | 5min |

**Signal normalization** (to 0-100 scale):

```python
def normalize_signal(raw_score: float, source: str) -> float:
    """Normalize signal to 0-100 scale per source."""
    if source == 'polymarket':
        # Convert probability (0.0-1.0) to score (0-100)
        return raw_score * 100
    elif source == 'reddit':
        # Log-normalized upvotes (0-100)
        return min(100, math.log1p(raw_score) * 15)
    elif source == 'hackernews':
        # Points + comments (0-100)
        return min(100, raw_score * 0.5)
    return raw_score  # Already normalized
```

### FR-5: Akash GPU Deployment

**A10G GPU (~$100-150/mo, 24GB VRAM, best price/perf for ML inference)**

```yaml
# akash/sdl/gpu-inference.yaml
version: "2.0"

services:
  kronos-api:
    image: kronos-euphoria/backend:latest
    expose:
      - port: 8000
        as: 8000
        to:
          - global: true
    env:
      - MODEL_NAME=NeoQuasar/Kronos-mini
      - DEVICE=cuda
      - REFRESH_SECONDS=60

profiles:
  compute:
    kronos-a10g:
      resources:
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a100
        cpu:
          units: 8
        memory:
          size: 32Gi
        storage:
          size: 100Gi

  placement:
    akash-a10g:
      pricing:
        kronos-a10g:
          denom: uact
          amount: 65000  # ~$130/mo at current ACT price

deployment:
  kronos-api:
    akash-a10g:
      profile: kronos-a10g
      count: 1
```

### FR-6: API Design

**Base URL**: `https://[akash-deployment]/api/v1`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | GET | Health check |
| `GET /predict?pair=ETHUSDT&horizon=5m` | GET | Kronos forecast |
| `GET /signals?pair=ETHUSDT` | GET | last30days signals |
| `GET /edge-score?pair=ETHUSDT` | GET | Fused Edge Score + zone recommendations |
| `GET /zones?pair=ETHUSDT` | GET | Zone grid with predictions |

**Response: `/edge-score`**

```json
{
  "pair": "ETHUSDT",
  "timestamp": "2026-05-15T16:23:11Z",
  "edge_score": 73.5,
  "confidence": "high",
  "direction": "up",
  "components": {
    "social_score": 68.2,
    "kronos_score": 82.0,
    "price_alignment": 0.78
  },
  "signals": {
    "reddit": {"score": 72, "posts": 24, "sentiment": "bullish"},
    "hackernews": {"score": 65, "stories": 8, "sentiment": "neutral"},
    "polymarket": {"score": 78, "odds": 0.78, "direction": "up"},
    "youtube": {"score": 58, "videos": 5, "sentiment": "bullish"}
  },
  "kronos_forecast": {
    "5m": {"direction": "up", "bias": 0.65, "confidence": 0.82},
    "15m": {"direction": "up", "bias": 0.58, "confidence": 0.75},
    "1h": {"direction": "neutral", "bias": 0.52, "confidence": 0.68}
  },
  "zones": [
    {"price": 3245.00, "edge_score": 71, "recommendation": "tap"},
    {"price": 3250.00, "edge_score": 78, "recommendation": "strong tap"},
    {"price": 3255.00, "edge_score": 83, "recommendation": "strong tap"},
    {"price": 3260.00, "edge_score": 65, "recommendation": "tap"},
    {"price": 3265.00, "edge_score": 42, "recommendation": "avoid"}
  ]
}
```

---

## Data Flow

```
[Social Signals]                    [ETH/USDT Price]
     │                                   │
     ▼                                   ▼
last30days ──────────┐     Alchemy ──────┘
     │               │          │
     ▼               ▼          ▼
[Signal Fusion]    [Kronos Inference]
     │               │
     └───────┬───────┘
             ▼
     [Edge Score Calculator]
             │
             ▼
     [API Endpoint /edge-score]
             │
             ▼
     [Dashboard Client]
             │
             ▼
     [Zone Grid + Prediction Overlay]
```

**Refresh cycle**:
1. Every 60s: Fetch ETH/USDT price from Alchemy
2. Every 60s: Run last30days on "ETH USDT" query
3. Every 60s: Run Kronos inference on recent OHLCV data
4. Fuse signals → Calculate Edge Score → Update dashboard

---

## Success Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Dashboard loads in < 3s on desktop | Lighthouse audit |
| 2 | Edge Score updates every 60s | Automated refresh verification test |
| 3 | Kronos returns 5m, 15m, 1h ETH/USDT forecasts | Unit test with mock OHLCV |
| 4 | last30days collects from 4+ sources | Integration test with mock responses |
| 5 | Edge Score formula matches spec | Property-based test |
| 6 | Akash T4 SDL deploys successfully | Provider bid received |
| 7 | API responds in < 500ms (excluding Kronos) | Load test |
| 8 | Dashboard works without API key requirements | Zero-config test |

---

## Open Questions

| # | Question | Options |
|---|----------|---------|
| 1 | **Dashboard refresh** | Manual refresh button (no auto-refresh) |
| 2 | **GPU selection** | A10G (~$100-150/mo, 24GB VRAM, best price/perf for ML inference) |
| 3 | **Zone width** | 1.0% (10 zones per 10% range) — verified actionable for euphoria betting |
| 4 | **YouTube transcripts** | Exclude for MVP (too slow for 60s target, focus on Reddit/HN/Polymarket) |
| 5 | **Historical backtesting** | Include — backtest Edge Score against past euphoria trades |

---

## API Cost Model (Clarification)

**Internal Akash inference: UNLIMITED calls**
- Dashboard → Kronos API calls on Akash: No rate limits, no API costs
- GPU compute is prepaid via ACT escrow, not per-call metering

**External data feeds (still applicable):**

| Source | Cost | Auth |
|--------|------|------|
| Binance OHLCV (ETH/USDT price) | Free tier available | Optional API key for higher limits |
| Reddit | Free (public JSON) | None |
| HackerNews | Free (Algolia API) | None |
| Polymarket | Free (Gamma API) | None |
| YouTube | Excluded for MVP | — |

**Conclusion**: Manual refresh is fine — no "API rate limit" concern for our own inference on Akash.

---

## References

- Kronos GitHub: https://github.com/shiyu-coder/Kronos
- Kronos HuggingFace: https://huggingface.co/NeoQuasar/Kronos-mini
- last30days skill: `/a0/usr/skills/last30days/`
- Akash skill: `/a0/usr/skills/akash/`
- euphoria's insight about zone-grid: Memory 2026-05-15 — "NO public API, it is a GAME/SIMULATION"

---

## Document History

| Date | Change | Author |
|------|--------|--------|
| 2026-05-15 | Initial spec from converged decisions | Tolu |
| 2026-05-15 | Updated decisions: manual refresh, A10G GPU, 1.0% zones, exclude YouTube, include backtesting. Added API cost model clarification. | Tolu |
