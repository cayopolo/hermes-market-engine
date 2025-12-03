-- ##########################################################
-- # THIS FILE HAS NOW BEEN DEPRECATED. KEEPING FOR REFERENCE
-- ##########################################################

-- Table: bid snapshots
-- id represents position in the order book (1 = best bid)
CREATE TABLE bid_orderbook_snapshot (
    id INTEGER PRIMARY KEY,
    price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL
);
-- Table: ask snapshots
-- id represents position in the order book (1 = best ask)
CREATE TABLE ask_orderbook_snapshot (
    id INTEGER PRIMARY KEY,
    price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL
);