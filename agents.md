# agents.md — Hermes Market Engine (Condensed)

Real-time market data system. Ingest Coinbase orderbook, compute analytics in-memory, expose via FastAPI.

---

## Architecture

Two concurrent services (`cli.py`):

* **Data Collection**

  * Connect Coinbase L2 WebSocket
  * Validate sequence numbers
  * Split flow:

    * **Hot path** → Redis (`hermes:market_data`) low-latency
    * **Cold path** → batch write Postgres ~10s

* **Analytics Engine**

  * Subscribe Redis
  * Maintain in-memory `OrderBook` per product (`SortedDict`)
  * Compute + cache analytics

* **API (FastAPI)**

  * Read in-memory state (no DB for live)
  * <1ms latency
  * Historical queries → Postgres

---

## Project Structure (key parts)

```
src/
  cli.py              # entrypoint
  config.py           # env settings
  data_models.py      # shared schemas

  data_collection/    # ingestion + Redis + DB batching
  analytics/          # orderbook + engine
  api/                # FastAPI routes, DI, DB, health

db/                   # schema + Timescale setup
tests/                # ingestion tests only
```

---

## Core Models

* `CoinbaseMessage` → raw WS message
* `CoinbaseEvent/Update` → orderbook changes
* `HotPathPacket` → Redis payload
* `Analytics` → spread, midprice, imbalance, VAMP

---

## Config

Defined in `Settings` (`.env` required)

Key fields:

* `product_ids` (default: ETH-EUR, XRP-USD)
* `redis_channel`
* DB batch interval/size
* DB pool sizes

---

## Running

```bash
docker-compose up -d
psql -f db/01-schema.sql
psql -f db/02-timescale-migration.sql
uv run hermes
```

API: `localhost:8000`
Docs: `/docs`

---

## API Overview

* `/analytics/*` → metrics (midprice, spread, imbalance, VAMP)
* `/orderbook/*` → live book
* `/history/raw-events` → DB queries
* `/health`

Return `503` until first snapshot (warm-up).

---

## Database

* **`raw_events_stream`**

  * Store raw messages (JSONB)
  * Idempotent `(connection_id, product_id, sequence_num)`

* **`orderbook_snapshot`**

  * Reconstructed book levels over time

Both use TimescaleDB (hypertables, compression, 120-day retention).

---

## Key Notes

* Coinbase sequence numbers **global**, not per product
* `size == 0` → delete level
* Bids desc, asks asc (`SortedDict`)
* Analytics **never hit DB** (in-memory only)
* Numba rejected: slower in prod

---

## Gaps

* Missing tests: analytics + API
* No snapshot history endpoint
* No dashboards

---
