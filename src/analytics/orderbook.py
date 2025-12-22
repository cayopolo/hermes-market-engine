import logging
from datetime import UTC, datetime
from decimal import Decimal
from operator import neg

from sortedcontainers import SortedDict

from src.data_models import Analytics, CoinbaseEvent

logger = logging.getLogger(__name__)


class OrderBook:
    """Maintains order book state for a single product"""

    def __init__(self, product_id: str):
        self.product_id = product_id
        self.bids = SortedDict(neg)  # Highest to lowest
        self.asks = SortedDict()  # Lowest to highest
        self.last_sequence = -1
        self.initialised = False

    def apply_event(self, event: CoinbaseEvent, sequence_num: int) -> bool:
        """
        Apply a Coinbase event to the order book.
        Returns True if successful, False if corruption detected.
        """
        # Snapshot events reset the orderbook completely - always apply them
        if event.type == "snapshot":
            self._apply_snapshot(event)
            self.initialised = True
            self.last_sequence = sequence_num
            logger.info("Snapshot applied: %s bids, %s asks, sequence reset to %s", len(self.bids), len(self.asks), sequence_num)
            return True

        # For updates, validate sequence
        if not self.initialised:
            if not hasattr(self, "_waiting_logged"):
                logger.warning("Order book not initialised. Waiting for snapshot event... (updates will be skipped)")
                self._waiting_logged = True
            return True  # Not fatal - snapshot will arrive soon

        if sequence_num <= self.last_sequence:
            logger.warning("Stale sequence: %s <= %s", sequence_num, self.last_sequence)
            return True  # Not fatal, just skip

        # Note: Sequence gaps are normal since Coinbase sequence numbers are global
        # across all products. We log large gaps as warnings but continue processing.
        if sequence_num != self.last_sequence + 1:
            gap_size = sequence_num - self.last_sequence - 1
            if gap_size > 10:
                logger.warning("Large sequence gap in analytics: %s -> %s (gap: %s)", self.last_sequence, sequence_num, gap_size)

        self._apply_update(event)
        self.last_sequence = sequence_num
        return True

    def _apply_snapshot(self, event: CoinbaseEvent) -> None:
        """Initialise order book from snapshot"""
        self.bids.clear()
        self.asks.clear()

        for update in event.updates:
            price = update.price_level
            qty = update.new_quantity

            if update.side == "bid":
                self.bids[price] = qty
            else:
                self.asks[price] = qty

    def _apply_update(self, event: CoinbaseEvent) -> None:
        """Apply incremental update"""
        for update in event.updates:
            price = update.price_level
            qty = update.new_quantity
            side = update.side

            book = self.bids if side == "bid" else self.asks

            if qty == 0:
                book.pop(price, None)
            else:
                book[price] = qty

    def get_analytics(self) -> Analytics:
        """Calculate current analytics"""
        best_bid = self.bids.keys()[0] if self.bids else None
        best_ask = self.asks.keys()[0] if self.asks else None

        spread = None
        midprice = None
        imbalance = None
        vamp = None
        vamp_n = None

        if best_bid and best_ask:
            spread = best_ask - best_bid
            midprice = (best_bid + best_ask) / Decimal("2")
            imbalance = self.imbalance()
            vamp = self.volume_adjusted_midprice()
            vamp_n = self.volume_adjusted_midprice_n()

        return Analytics(
            product_id=self.product_id,
            timestamp=datetime.now(UTC),
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            midprice=midprice,
            imbalance=imbalance,
            volume_adjusted_midprice=vamp,
            volume_adjusted_midprice_n=vamp_n,
        )

    def imbalance(self) -> Decimal:
        """Calculate static order book imbalance

        Imbalance = (sum of bid quantities - sum of ask quantities) / (sum of bid quantities + sum of ask quantities)

        Returns:
            Decimal: Imbalance value between -1 and 1, where positive indicates more bid volume
        """
        bids_sum = sum(self.bids.values())
        asks_sum = sum(self.asks.values())

        return Decimal((bids_sum - asks_sum) / (bids_sum + asks_sum) if (bids_sum + asks_sum) > 0 else 0.0)

    def volume_adjusted_midprice(self) -> float | None:
        """Calculate volume-adjusted midprice

        Volume-adjusted midprice = (p_best_bid X Q_best_ask + p_best_ask X Q_best_bid) / (Q_best_bid + Q_best_ask)

        Note: price and quantity are cross-multiplied between bid and ask sides.
        Returns:
            float: Volume-adjusted midprice
        """
        if not self.bids or not self.asks:
            return None

        best_bid_price = self.bids.keys()[0]
        best_ask_price = self.asks.keys()[0]

        best_bid_qty = self.bids[self.bids.keys()[0]]
        best_ask_qty = self.asks[self.asks.keys()[0]]

        total_qty = best_bid_qty + best_ask_qty

        if total_qty == 0:
            return None

        return (best_bid_price * best_ask_qty + best_ask_price * best_bid_qty) / total_qty

    def volume_adjusted_midprice_n(self, depth_percent: float = 1.0) -> float | None:
        """Calculate volume-adjusted midprice with n% market depth

        Aggregates quantities within n% of the midprice on each side, then applies VAMP formula.
        For 1% market depth: bid side from mid x 0.99 to mid, ask side from mid to mid x 1.01

        Args:
            depth_percent: Percentage depth (default 1.0 for 1% market depth)

        Returns:
            float: Volume-adjusted midprice within n% depth
        """
        if not self.bids or not self.asks:
            return None

        best_bid_price = self.bids.keys()[0]
        best_ask_price = self.asks.keys()[0]
        midprice = (best_bid_price + best_ask_price) / 2.0

        # Calculate depth bounds
        depth_factor = depth_percent / 100.0
        bid_lower_bound = midprice * (1.0 - depth_factor)
        ask_upper_bound = midprice * (1.0 + depth_factor)

        # Aggregate quantities within depth on each side
        bid_qty_n = 0.0
        for price, qty in self.bids.items():
            if price >= bid_lower_bound:
                bid_qty_n += qty
            else:
                break  # bids are sorted highest to lowest, so stop when below bound

        ask_qty_n = 0.0
        for price, qty in self.asks.items():
            if price <= ask_upper_bound:
                ask_qty_n += qty
            else:
                break  # asks are sorted lowest to highest, so stop when above bound

        total_qty = bid_qty_n + ask_qty_n

        if total_qty == 0:
            return None

        vamp_n = (best_bid_price * ask_qty_n + best_ask_price * bid_qty_n) / total_qty
        return vamp_n
