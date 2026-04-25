# agents.md — Hermes Market Engine

A real-time market data platform that ingests live orderbook data from Coinbase and exposes analytics through a FastAPI HTTP layer. Learning-driven, but production-inspired.

---

## Project Layout

```
src/
  cli.py                        # Entry point: `uv run hermes`
  config.py                     # Pydantic Settings (all env vars)
  data_models.py                # Shared Pydantic models (CoinbaseMessage, HotPathPacket, Analytics, …)
  logging_config.py

  data_collection/
    ingestor.py                 # DataCollectionService — orchestrates ingestion
    coinbase_client.py          # CoinbaseWebsocketClient — WebSocket connection + backoff
    publisher.py                # Redis publisher (hot path)
    batched_writer.py           # BatchedDBWriter — cold path, time-based flush to Postgres

  analytics/
    orderbook.py                # OrderBook — SortedDict-backed in-memory book per product
    engine.py                   # OrderbookManager — subscribes to Redis, drives analytics

  api/
    main.py                     # FastAPI app factory + lifespan
    analytics.py                # GET /analytics/* routes
    orderbook.py                # GET /orderbook/* routes
    history.py                  # GET /history/* routes
    responses.py                # Pydantic response models
    dependencies.py             # FastAPI DI (injects OrderbookManager)
    db.py                       # asyncpg pool for history queries
    health.py                   # GET /health

db/
  01-schema.sql                 # Core tables (raw_events_stream, orderbook_snapshot)
  02-timescale-migration.sql    # TimescaleDB hypertables + compression + retention
  raw_events_stream_schema.sql
  order_book_snapshot_schema.sql

tests/
  data_collection/
    test_coinbase_client.py
```

---

## Architecture in One Paragraph

Two services run concurrently (launched via `src/cli.py`). The **Data Collection Service** (`ingestor.py`) connects to Coinbase's level2 WebSocket, validates sequence numbers, then fans each message out to two paths: the **hot path** publishes a `HotPathPacket` to Redis (`hermes:market_data`) for sub-millisecond delivery, and the **cold path** buffers messages in a `deque` and batch-writes them to Postgres every 10 s. The **Analytics Service** (`engine.py`) subscribes to the Redis channel, applies events to an in-memory `OrderBook` per product (backed by `SortedDict` for O(log n) bid/ask access), and caches computed analytics. The **FastAPI layer** (`api/`) reads analytics and orderbook state directly from that in-memory engine — no DB round-trip — and provides `<1ms` read latency. Historical data comes from Postgres via the `/history` router.

---

## Key Data Models (`src/data_models.py`)

| Model | Purpose |
|---|---|
| `CoinbaseUpdate` | One price-level change: side, price, quantity |
| `CoinbaseEvent` | Array of updates with type (`snapshot` \| `update`) and `product_id` |
| `CoinbaseMessage` | Full WebSocket message: `channel`, `sequence_num`, `timestamp`, `events[]` |
| `HotPathPacket` | Redis envelope: `ts_ingest`, `connection_id`, `payload` (CoinbaseMessage) |
| `Analytics` | Computed snapshot: spread, midprice, imbalance, VAMP, VAMP_n |

---

## Configuration (`src/config.py`)

All config is in `Settings(BaseSettings)` and read from `.env`. Key fields:

```python
product_ids: list[str]          # default: ["ETH-EUR", "XRP-USD"]
redis_channel: str              # default: "hermes:market_data"
db_batch_interval_seconds: float  # default: 10.0
db_batch_size: int              # default: 1000
db_pool_min_size / max_size     # default: 2 / 10
```

Copy `.env.example` to `.env` and set `DB_PASSWORD` at minimum.

---

## Running the Project

```bash
# 1. Start infrastructure
docker-compose up -d   # Postgres (TimescaleDB) + Redis

# 2. Apply schema (first time only)
psql -U postgres -d hermes_market_engine -f db/01-schema.sql
psql -U postgres -d hermes_market_engine -f db/02-timescale-migration.sql

# 3. Run all services
uv run hermes

# Optional: debug logging
uv run hermes --log-level debug
```

Services started: Data Collection, Analytics Engine, FastAPI on `http://localhost:8000`.

---

## Running Tests

```bash
uv run pytest
```

Tests live in `tests/`. Current coverage is `data_collection/` only. Pytest config is in `pyproject.toml` (`[tool.pytest.ini_options]`).

---

## Linting & Formatting

Ruff handles both. Config is in `pyproject.toml` (`[tool.ruff]`). Line length is 140.

```bash
uv run ruff check .      # lint (auto-fixes where possible)
uv run ruff format .     # format
```

The `fix = true` flag means `ruff check` applies safe auto-fixes automatically.

---

## API Quick Reference

Base URL: `http://localhost:8000`

| Method | Path | Notes |
|---|---|---|
| GET | `/analytics/products` | List configured product IDs |
| GET | `/analytics/current/{product_id}` | Full snapshot (spread, midprice, imbalance, VAMP) |
| GET | `/analytics/midprice/{product_id}` | Mid-price only |
| GET | `/analytics/spread/{product_id}` | Bid-ask spread |
| GET | `/analytics/imbalance/{product_id}` | −1 to 1, positive = more bids |
| GET | `/analytics/vamp/{product_id}` | Volume-adjusted midprice (best level) |
| GET | `/analytics/vamp_n/{product_id}?depth_percent=1.0` | VAMP at n% market depth |
| GET | `/orderbook/snapshot/{product_id}?depth=10` | Top N bid/ask levels |
| GET | `/orderbook/bids/{product_id}?depth=10` | Best bid levels |
| GET | `/orderbook/asks/{product_id}?depth=10` | Best ask levels |
| GET | `/orderbook/depth/{product_id}` | Total levels in book |
| GET | `/history/raw-events?product_id=&start_time=&end_time=` | Cold-path query |
| GET | `/health` | Health check |

All product-specific endpoints return `503` until the first orderbook snapshot arrives from Coinbase (normal during warm-up).

Swagger UI: `http://localhost:8000/docs`

---

## Database Schema

**`raw_events_stream`** — cold path storage. Keyed on `(connection_id, product_id, sequence_num)` with `ON CONFLICT DO NOTHING` for idempotency. Full raw JSONB stored for replay.

**`orderbook_snapshot`** — periodic reconstructed orderbook snapshots written by the analytics engine. Each row is one price level (`side`, `price`, `quantity`, `snapshot_time`).

Both tables are TimescaleDB hypertables with compression and a 120-day retention policy.

---

## Important Implementation Notes

- **Sequence numbers are global** across all Coinbase products. Gaps between sequence numbers for a single product are normal and should not trigger reconnection (unlike gaps in the data collection service, which tracks global sequence and restarts on true gaps > 1).
- **Bids are stored descending** in `SortedDict(neg)`, asks ascending in `SortedDict()`. Never change this without updating all callers.
- **`size == 0` means remove the level.** The Coinbase level2 protocol signals deletions by sending `new_quantity = 0`.
- **JIT (Numba) was tested and rejected.** Synthetic benchmarks showed 20-36% speedup, but production testing showed an 81% *slowdown* due to data conversion overhead. Pure Python is faster for streaming analytics at this message rate. See `docs/JIT_PERFORMANCE_ANALYSIS.md`.
- **Analytics reads never hit the database.** The `OrderbookManager` is injected into FastAPI via `dependencies.py`. Adding a DB call to a `/analytics` or `/orderbook` route would be a regression.

---

## Known Gaps / Planned Work

- Tests only cover `data_collection/`. Analytics and API layers are untested.
- No `/history` endpoint for `orderbook_snapshot` table (only `raw_events_stream` is queryable).
- No dashboards.
