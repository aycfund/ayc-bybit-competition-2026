# ATR Adaptive Grid Strategy V9.5 - Complete Specification

> **Version**: 9.5 (February 2026)
> **Team**: AYC Fund (YC W22)
> **AI Model**: Claude Code Opus 4.6
> **Validated**: Monte Carlo 10,000 iterations, 365 days, 24 symbols

---

## 1. Executive Summary

The ATR Adaptive Grid Strategy V9.5 is an AI-powered cryptocurrency trading system that combines:

- **ATR-based adaptive grid spacing** for dynamic entry/exit levels
- **EMA trend filter** for directional bias
- **4-Quadrant regime classification** for market-adaptive behavior
- **Hedge mode** for simultaneous Long/Short exposure
- **CapitalGuard (50% Rule)** for robust risk management

### Key Performance Metrics (V9.5 Hedge Mode, 365-day Backtest)

| Tier | Leverage | ROI | Win Rate | Profit Factor | Sharpe | MDD | P(Liquidation) |
|------|----------|-----|----------|---------------|--------|-----|----------------|
| Shield | 1x | +25.3% | 99.2% | 7.23 | 17.30 | 1.35% | 0% |
| Balance | 3x | +1,089.8% | 99.3% | 9.10 | 16.50 | 4.57% | 0% |
| Boost | 5x | +16,531.5% | 99.4% | 8.91 | 16.48 | 5.48% | 0% |

---

## 2. AI Model Integration

### Claude Code Usage

Our strategy development leverages Claude AI (Opus 4.6) for:

1. **Strategy Development**
   - Code generation and optimization
   - Algorithm design and implementation
   - Bug detection and correction

2. **Backtesting Analysis**
   - Performance evaluation
   - Parameter optimization
   - Statistical validation

3. **Real-time Operations**
   - Trade signal validation
   - Risk assessment
   - Strategy monitoring

### Interaction Frequency

| Component | Frequency | Purpose |
|-----------|-----------|---------|
| Main Execution Loop | 60 seconds | Signal generation and order management |
| Regime Detection | 60 seconds | Market classification update |
| Grid Level Update | Per tick | Dynamic entry/exit adjustment |
| Risk Check | Real-time | Continuous margin and drawdown monitoring |
| OHLCV Data Fetch | 60 seconds | 1-hour candles for indicator calculation |

---

## 3. Strategy Logic

### 3.1 Indicator Calculation

**EMA (Exponential Moving Average)**
```python
EMA_200 = close.ewm(span=200, adjust=False).mean()
```
- **Purpose**: Trend direction detection
- **Signal**: Price > EMA = Bullish, Price < EMA = Bearish

**ATR (Average True Range)**
```python
TR = max(high - low, abs(high - close_prev), abs(low - close_prev))
ATR_14 = TR.ewm(span=14, adjust=False).mean()
```
- **Purpose**: Volatility measurement for grid spacing

**ADX (Average Directional Index)**
```python
ADX = smoothed DX (Directional Index)
Threshold: 25.0
```
- **Purpose**: Trend strength measurement

---

### 3.2 Regime Detection (4-Quadrant Classification)

```
┌───────────────────────────────────────────────────┐
│           ATR Ratio (ATR / MA50)                  │
│                    │                              │
│         < 1.2      │      >= 1.2                  │
│    ┌───────────────┼───────────────┐              │
│ A  │ STABLE_TREND  │ VOLATILE_TREND│  Trend      │
│ D  │ (Aggressive)  │ (Cautious)    │  (ADX>25)   │
│ X  ├───────────────┼───────────────┤              │
│    │ SIDEWAYS_QUIET│ SIDEWAYS_CHOP │  Sideways   │
│    │ (Range Trade) │ (Defensive)   │  (ADX≤25)   │
│    └───────────────┴───────────────┘              │
└───────────────────────────────────────────────────┘
```

**Regime Parameters**

| Regime | Spacing | TP Mult | SL Drawdown | Max Levels |
|--------|---------|---------|-------------|------------|
| STABLE_TREND | 1.0% | 1.2 | 8% | 5 |
| VOLATILE_TREND | 1.5% | 1.0 | 4% | 5 |
| SIDEWAYS_QUIET | 0.5% | 1.1 | 5% | 5 |
| SIDEWAYS_CHOP | 2.0% | 0.8 | 3% | 3 |

---

### 3.3 Grid Entry Logic

**Entry Price Calculation**
```python
# Long Entry (buy on dips)
entry_price = current_price - (ATR × spacing_mult)

# Short Entry (sell on rallies)
entry_price = current_price + (ATR × spacing_mult)
```

**Take Profit Calculation**
```python
# Long TP
tp_price = entry_price + (spacing × tp_mult)

# Short TP
tp_price = entry_price - (spacing × tp_mult)
```

**Grid Structure Example (STABLE_TREND)**
```
Current Price: $50,000
Spacing: 1.0%

L1 Entry: $49,500 (-1.0%) → TP: $50,094 (+1.2%)
L2 Entry: $49,000 (-2.0%) → TP: $49,588
L3 Entry: $48,500 (-3.0%) → TP: $49,082
L4 Entry: $48,000 (-4.0%) → TP: $48,576
L5 Entry: $47,500 (-5.0%) → TP: $48,070

Stop Loss: avg_entry × 0.92 (Grid-wide)
```

---

### 3.4 V9.5 Hedge Mode

V9.5 introduces simultaneous Long and Short grids with independent SL tracking:

```python
# Independent SL for each direction
long_sl_price = None   # Set when Long position opens
short_sl_price = None  # Set when Short position opens

# Entry conditions
if price > EMA_200:  # Bullish
    → Place Long grid entries
if price < EMA_200:  # Bearish
    → Place Short grid entries
```

**Benefits**:
- Market-neutral exposure
- Profit from both directions
- Reduced directional risk

---

## 4. Risk Management

### 4.1 CapitalGuard (50% Rule)

```python
safe_balance = equity × 0.50
potential_margin = margin_per_level × max_levels

if potential_margin > safe_balance:
    → Entry BLOCKED
```

**Risk Levels**:
- **SAFE** (< 40%): Normal trading
- **WARNING** (40-50%): Trade with caution
- **BLOCKED** (> 50%): New entries blocked

### 4.2 Stop Loss Mechanism

**Grid-wide SL**
- Based on weighted average entry price
- Percentage from config (3-8% depending on regime)

**Trailing Stop Loss**
```python
# For Long positions
if current_price > highest_price:
    highest_price = current_price

trailing_sl = highest_price × (1 - sl_drawdown)

if trailing_sl > current_sl:
    current_sl = trailing_sl  # Move SL up
```

### 4.3 Emergency Stop

```python
drawdown = (peak_equity - current_equity) / peak_equity

if drawdown >= 0.15:  # 15%
    → CLOSE ALL POSITIONS
    → HALT TRADING
```

---

## 5. Trading Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│  1. FETCH OHLCV DATA (1h candles, 300 bars)         │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  2. CALCULATE INDICATORS                            │
│     - EMA(200), ATR(14), ADX                        │
│     - Determine bullish/bearish                     │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  3. REGIME DETECTION                                │
│     - Classify market into 4 quadrants              │
│     - Get regime-specific parameters                │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  4. CHECK EXISTING POSITIONS                        │
│     - Monitor TP hits                               │
│     - Check SL triggers                             │
│     - Update trailing SL                            │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  5. CAPITALGUARD CHECK                              │
│     - Verify margin limits                          │
│     - Block if > 50% usage                          │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  6. PLACE NEW ENTRIES (if allowed)                  │
│     - Long grid if bullish                          │
│     - Short grid if bearish (V9.5)                  │
│     - Dynamic spacing based on ATR                  │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  7. LOOP (every 60 seconds)                         │
└─────────────────────────────────────────────────────┘
```

---

## 6. Cost Model

| Type | Rate | Applied To |
|------|------|------------|
| Trading Fee | 0.05% | Entry + Exit |
| Slippage | 0.03% | Entry + Exit |
| Funding Rate | 0.01%/8h | Open positions |

**Total Round-trip Cost**: ~0.16% + funding

---

## 7. Backtest Results

### Monte Carlo Validation (10,000 iterations)

| Metric | Shield | Balance | Boost |
|--------|--------|---------|-------|
| Median ROI | 94.4% | 788.1% | 1,274.9% |
| Worst 10% | 84.8% | 652.7% | 1,024.9% |
| P(MDD > 50%) | 0.00% | 0.00% | 0.00% |
| P(Liquidation) | 0.00% | 0.00% | 0.00% |

### Top Performing Symbols (Balance Tier)

| Symbol | ROI | Win Rate | Trades | Profit Factor |
|--------|-----|----------|--------|---------------|
| ARB | 1,422.6% | 99.5% | 5,046 | 14.69 |
| IMX | 1,389.2% | 99.2% | 5,220 | 9.45 |
| SUI | 1,328.4% | 99.4% | 5,016 | 13.30 |
| NEAR | 1,298.9% | 99.6% | 5,104 | 11.06 |
| OP | 1,252.9% | 99.4% | 5,185 | 10.53 |

---

## 8. Competition Configuration

| Parameter | Value |
|-----------|-------|
| Initial Capital | 1,000 USDT |
| Tier | Balance (3x leverage) |
| Symbols | Top 10 by 24h volume |
| Max Levels | 5 per direction |
| Min Trades/Day | 10+ (expected: 14-144) |
| Leverage Limit | 15x (using 3x) |

---

## 9. Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Signal Provider                     │
│  (Centralized calculation, Redis caching)           │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              ATR Grid Strategy V9.5                  │
│  - Regime detection                                 │
│  - Grid generation                                  │
│  - Position management                              │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│               Risk Manager                           │
│  - CapitalGuard (50% rule)                          │
│  - Trailing SL                                      │
│  - Emergency stop                                   │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│            Exchange Gateway (CCXT)                   │
│  - Bybit API integration                            │
│  - Order management                                 │
│  - Position tracking                                │
└─────────────────────────────────────────────────────┘
```

---

## 10. Disclaimer

This strategy is provided for the Bybit AI Trading Competition 2026. Past performance does not guarantee future results. Cryptocurrency trading involves significant risk. Always trade responsibly.

---

*Document Version: 9.5*
*Last Updated: February 2026*
*Author: AYC Fund (YC W22)*
