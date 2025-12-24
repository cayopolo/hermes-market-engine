# JIT Performance Analysis

## Summary

**Conclusion**: Numba JIT compilation provides **no benefit** for real-time orderbook analytics in a streaming data environment. The original Python implementation is **~81% faster** than the JIT-optimised version in production.

## Benchmark vs Production Results

### Synthetic Benchmarks (Misleading)
- **Test**: 100 iterations on static orderbooks
- **Result**: JIT showed 20-36% speedup
- **Why misleading**: Arrays created once, computation measured in isolation

### Production Environment (Real Performance)
- **Test**: Live market data streaming from Coinbase WebSocket
- **Result**: JIT is 81% **slower** (1.43ms vs 0.79ms per analytics calculation)

| Method | Mean Latency | Median | P95 | P99 |
|--------|--------------|--------|-----|-----|
| Original Python | 0.79ms | 0.75ms | 1.36ms | 1.62ms |
| JIT-Optimised | 1.43ms | 1.34ms | 2.40ms | 2.66ms |

## Root Cause: Data Conversion Overhead

The JIT version requires converting `SortedDict` → `list` → `numpy.ndarray` on every call:

```python
# Executed on EVERY analytics calculation:
bid_prices_list = list(self.bids.keys())           # Copy 1
bid_qtys_list = list(self.bids.values())           # Copy 2  
bid_qtys = np.asarray(bid_qtys_list, dtype=float)  # Copy 3 + dtype conversion
bid_prices = np.asarray(bid_prices_list, dtype=float) # Copy 4 + dtype conversion
```

For typical BTC-USD orderbook (~200 levels/side):
- **Conversion overhead**: ~0.6-0.7ms
- **JIT computation savings**: ~0.1-0.2ms
- **Net result**: 2x slower

## Where JIT Could Help

JIT optimisation makes sense when:
- Arrays are **reused** across multiple calculations
- Working with **very deep** orderbooks (>1000 levels)
- **Batch processing** where conversion is amortised over many operations

None of these apply to streaming real-time market data.

## Implementation Decision

**Production uses**: `get_analytics()` - the original Python implementation
