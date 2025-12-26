-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert raw_events_stream to hypertable
SELECT create_hypertable(
    'raw_events_stream',
    'exchange_timestamp',
    chunk_time_interval => INTERVAL '1 day',
    create_default_indexes => FALSE,
    if_not_exists => TRUE
);

-- Convert orderbook_snapshot to hypertable
SELECT create_hypertable(
    'orderbook_snapshot',
    'snapshot_time',
    chunk_time_interval => INTERVAL '1 day',
    create_default_indexes => FALSE,
    if_not_exists => TRUE
);

-- Compress data older than 7 days to save disk space
ALTER TABLE raw_events_stream SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'product_id, connection_id',
    timescaledb.compress_orderby = 'exchange_timestamp DESC'
);

SELECT add_compression_policy('raw_events_stream', INTERVAL '7 days');

ALTER TABLE orderbook_snapshot SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'product_id',
    timescaledb.compress_orderby = 'snapshot_time DESC'
);

SELECT add_compression_policy('orderbook_snapshot', INTERVAL '7 days');

-- Retention Policy: Automatically drop data older than 90 days
SELECT add_retention_policy('raw_events_stream', INTERVAL '120 days');
SELECT add_retention_policy('orderbook_snapshot', INTERVAL '120 days');

