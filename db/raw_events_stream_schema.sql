-- Table: raw_events_stream
-- Stores the raw, unprocessed WebSocket messages from the exchange.

CREATE TABLE raw_events_stream (
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
-- Indexes to improve lookup performance
CREATE INDEX idx_raw_events_time ON raw_events_stream (product_id, exchange_timestamp DESC);
CREATE INDEX idx_raw_events_exchange_ts ON raw_events_stream (exchange_timestamp);
CREATE INDEX idx_raw_events_channel ON raw_events_stream (channel);