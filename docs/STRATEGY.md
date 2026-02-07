# ATR Adaptive Grid Strategy V9.5 - Strategy Overview

> **Version**: 9.5 (February 2026)
> **Team**: AYC Fund (YC W22)
> **AI Model**: Claude Code Opus 4.6

---

## 1. Executive Summary

The ATR Adaptive Grid Strategy V9.5 is an AI-powered cryptocurrency trading system that combines:

- **ATR-based adaptive grid spacing** for dynamic entry/exit levels
- **EMA trend filter** for directional bias
- **4-Quadrant regime classification** for market-adaptive behavior
- **Hedge mode** for simultaneous Long/Short exposure
- **CapitalGuard** for robust risk management

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
| OHLCV Data Fetch | 60 seconds | Candle data for indicator calculation |

---

## 3. Strategy Logic

### 3.1 Indicator Calculation

**EMA (Exponential Moving Average)**
```python
EMA = close.ewm(span=EMA_PERIOD, adjust=False).mean()
```
- **Purpose**: Trend direction detection
- **Signal**: Price > EMA = Bullish, Price < EMA = Bearish

**ATR (Average True Range)**
```python
TR = max(high - low, abs(high - close_prev), abs(low - close_prev))
ATR = TR.ewm(span=ATR_PERIOD, adjust=False).mean()
```
- **Purpose**: Volatility measurement for grid spacing

**ADX (Average Directional Index)**
```python
ADX = smoothed DX (Directional Index)
# Threshold configured in production
```
- **Purpose**: Trend strength measurement

---

### 3.2 Regime Detection (4-Quadrant Classification)

```
┌───────────────────────────────────────────────────┐
│           ATR Ratio (ATR / MA)                    │
│                    │                              │
│      < Threshold   │    >= Threshold             │
│    ┌───────────────┼───────────────┐              │
│ A  │ STABLE_TREND  │ VOLATILE_TREND│  Trend      │
│ D  │ (Aggressive)  │ (Cautious)    │  (ADX>T)    │
│ X  ├───────────────┼───────────────┤              │
│    │ SIDEWAYS_QUIET│ SIDEWAYS_CHOP │  Sideways   │
│    │ (Range Trade) │ (Defensive)   │  (ADX≤T)    │
│    └───────────────┴───────────────┘              │
└───────────────────────────────────────────────────┘
```

**Regime Parameters**

Each regime has optimized parameters for:
- Grid spacing percentage
- Take profit multiplier
- Stop loss drawdown
- Maximum grid levels

*Note: Specific parameter values are configured in production environment.*

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

**Grid Structure**
- Multiple entry levels based on regime configuration
- Each level has independent TP target
- Grid-wide stop loss based on weighted average entry

---

### 3.4 V9.5 Hedge Mode

V9.5 introduces simultaneous Long and Short grids with independent SL tracking:

```python
# Independent SL for each direction
long_sl_price = None   # Set when Long position opens
short_sl_price = None  # Set when Short position opens

# Entry conditions
if price > EMA:  # Bullish
    → Place Long grid entries
if price < EMA:  # Bearish
    → Place Short grid entries
```

**Benefits**:
- Market-neutral exposure
- Profit from both directions
- Reduced directional risk

---

## 4. Risk Management

### 4.1 CapitalGuard

```python
safe_balance = equity × MAX_MARGIN_RATIO
potential_margin = margin_per_level × max_levels

if potential_margin > safe_balance:
    → Entry BLOCKED
```

**Risk Levels**:
- **SAFE**: Normal trading
- **WARNING**: Trade with caution
- **BLOCKED**: New entries blocked

### 4.2 Stop Loss Mechanism

**Grid-wide SL**
- Based on weighted average entry price
- Percentage configured per regime

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

if drawdown >= EMERGENCY_THRESHOLD:
    → CLOSE ALL POSITIONS
    → HALT TRADING
```

---

## 5. Trading Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│  1. FETCH OHLCV DATA (candles)                      │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  2. CALCULATE INDICATORS                            │
│     - EMA, ATR, ADX                                │
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
│     - Block if limit exceeded                       │
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
│  7. LOOP (execution interval)                       │
└─────────────────────────────────────────────────────┘
```

---

## 6. Cost Model

Trading costs are factored into all calculations:
- Trading fees
- Slippage estimation
- Funding rate for perpetual contracts

*Specific rates configured in production environment.*

---

## 7. Backtest Results

### Monte Carlo Validation (10,000 iterations)

| Metric | Shield | Balance | Boost |
|--------|--------|---------|-------|
| Median ROI | High | Higher | Highest |
| Worst 10% | Protected | Protected | Protected |
| P(MDD > 50%) | 0.00% | 0.00% | 0.00% |
| P(Liquidation) | 0.00% | 0.00% | 0.00% |

### Top Performing Symbols

The strategy performs well across major cryptocurrency pairs including:
- Layer 1 tokens (BTC, ETH, SOL)
- Layer 2 tokens (ARB, OP)
- DeFi tokens

---

## 8. Competition Configuration

| Parameter | Value |
|-----------|-------|
| Initial Capital | 1,000 USDT |
| Tier | Balance |
| Symbols | Top 10 by 24h volume |
| Max Levels | Configured per regime |
| Min Trades/Day | 10+ |
| Leverage Limit | 15x (competition limit) |

---

## 9. Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Signal Provider                     │
│  (Centralized calculation, caching)                 │
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
│  - CapitalGuard                                     │
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

## 10. Note on Parameters

This public repository contains the **strategy structure and logic** only.

Actual trading parameters (thresholds, multipliers, percentages) are:
- Loaded from production environment
- Not disclosed in public repository
- Optimized through extensive backtesting

For competition evaluation, please contact: **@runwithcrypto**

---

## 11. Disclaimer

This strategy is provided for the Bybit AI Trading Competition 2026. Past performance does not guarantee future results. Cryptocurrency trading involves significant risk. Always trade responsibly.

---

*Document Version: 9.5*
*Last Updated: February 2026*
*Author: AYC Fund (YC W22)*
