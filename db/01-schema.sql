-- ============================================================================
-- TABLE: raw_events_stream
-- Purpose: Cold Path storage for all raw WebSocket messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_events_stream (
    -- Unique internal primary key for referencing the event record.
    id BIGSERIAL PRIMARY KEY,
    -- Generate on each connection
    connection_id UUID NOT NULL,
    -- Exchange-provided sequence number.
    sequence_num BIGINT NOT NULL,
    -- The trading pair (e.g., 'EOS-USD').
    product_id TEXT NOT NULL,
    -- The channel the event came from (e.g., 'l2_data', 'subscriptions', 'ticker').
    channel TEXT NOT NULL,
    -- Exchange-provided timestamp (when the event occurred).
    exchange_timestamp TIMESTAMPTZ NOT NULL,
    -- Our server's timestamp (when the message was received).
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Event type: 'snapshot' or 'update'.
    event_type TEXT NOT NULL,
    -- Full, raw JSON payload.
    raw_message JSONB NOT NULL,
    CONSTRAINT ws_events_sequence_unique UNIQUE (connection_id, product_id, sequence_num)
);

-- ============================================================================
-- INDEXES for raw_events_stream
-- ============================================================================
-- Primary query pattern: Get events for a product in time range
CREATE INDEX idx_raw_events_product_time ON raw_events_stream(product_id, exchange_timestamp DESC);

-- For sequence gap analysis and replay
CREATE INDEX idx_raw_events_sequence ON raw_events_stream(connection_id, sequence_num);

-- For channel-specific queries
CREATE INDEX idx_raw_events_channel ON raw_events_stream(channel)
WHERE channel != 'subscriptions';

-- For sequence gap analysis and replay
CREATE INDEX idx_raw_events_sequence ON raw_events_stream(connection_id, sequence_num);
-- For channel-specific queries
CREATE INDEX idx_raw_events_channel ON raw_events_stream(channel)
WHERE channel != 'subscriptions';
-- Partial index excludes noise
-- For time-based queries (analytics, cleanup jobs)
CREATE INDEX idx_raw_events_ingest_time ON raw_events_stream(ingest_timestamp DESC);


-- ============================================================================
-- TABLE: orderbook_snapshot
-- Purpose: Periodic snapshots of reconstructed order book state
-- ============================================================================
CREATE TABLE IF NOT EXISTS orderbook_snapshot (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('bid', 'ask')),
    price NUMERIC(20, 8) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    snapshot_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sequence_num BIGINT,
    -- Unique price levels per snapshot
    CONSTRAINT unique_snapshot_level UNIQUE (product_id, snapshot_time, side, price)
);

-- ============================================================================
-- INDEXES for orderbook_snapshot
-- ============================================================================

-- Get latest snapshot for a product
CREATE INDEX idx_orderbook_snapshot_latest
    ON orderbook_snapshot(product_id, snapshot_time DESC);

-- For time-range queries
CREATE INDEX idx_orderbook_snapshot_time
    ON orderbook_snapshot(snapshot_time DESC);
