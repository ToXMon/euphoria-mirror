# Kronos Euphoria Mirror

Real-time ETH prediction mirror for [euphoria.finance](https://euphoria.finance) - Kronos time-series model + social signals + edge scoring.

```
+--------------------------------------------------+
|                   Dashboard                       |
|  +----------+ +----------+ +------------------+   |
|  | ETH/USDT | |  Zones   | |   Edge Score     |   |
|  |  Price   | |  Grid    | |   0-100          |   |
|  +----------+ +----------+ +------------------+   |
|                                                   |
|  +----------------------------------------------+ |
|  |  Signal Breakdown + Kronos Forecast          | |
|  +----------------------------------------------+ |
+--------------------------------------------------+
         ^                    ^
         |                    |
+--------+--------+ +--------+--------+
| FastAPI Backend  | |  Binance API    |
| + Kronos Model   | |  (ETH OHLCV)    |
| (HuggingFace)    | |                 |
+------------------+ +-----------------+
         ^                    ^
         |                    |
+--------+--------+ +--------+--------+
| Akash GPU       | | last30days      |
| (A10G)          | | Social Signals  |
+------------------+ +-----------------+
```

## Quick Start (Docker)

```bash
# Build
docker build -t euphoria-mirror .

# Run (CPU mode)
docker run -p 8000:8000 euphoria-mirror

# Run (GPU mode)
docker run --gpus all -p 8000:8000 \
  -e GPU_ENABLED=true \
  euphoria-mirror
```

Open http://localhost:8000 for the dashboard.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KRONOS_TOKENIZER` | `NeoQuasar/Kronos-Tokenizer-base` | HuggingFace tokenizer |
| `KRONOS_MODEL` | `NeoQuasar/Kronos-small` | HuggingFace model |
| `KRONOS_MAX_CONTEXT` | `512` | Max context window |
| `GPU_ENABLED` | `false` | Enable GPU inference |
| `BINANCE_BASE_URL` | `https://api.binance.com` | Binance API endpoint |
| `HF_TOKEN` | _(empty)_ | HuggingFace auth token |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

Copy `.env.example` to `.env` and customize.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/health` | GET | Health check |
| `/api/predictions` | GET | Kronos ETH predictions |
| `/api/signals` | GET | Social signal breakdown |
| `/api/edge-score` | GET | Combined edge score |

## Akash Deployment (GPU)

Deploy to Akash Network with A10G GPU:

```bash
# Install provider-services CLI
# Fund wallet with AKT/ACT

# Deploy
provider-services tx deployment create akash/sdl/gpu-inference.yaml \
  --from my-key --chain-id akashnet-2
```

The SDL pulls `ghcr.io/toxmon/euphoria-mirror:latest` with GPU enabled.

## Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

uvicorn backend.main:app --reload --port 8000
```

## Tech Stack

- **Backend**: FastAPI, Pydantic, Uvicorn
- **ML**: Kronos (time-series), PyTorch, Transformers, HuggingFace Hub
- **Data**: Binance API (ETH/USDT OHLCV), last30days (social signals)
- **Frontend**: Vanilla HTML/JS/CSS
- **Infra**: Docker, GitHub Actions CI/CD, GHCR, Akash Network (GPU)

## License

MIT
