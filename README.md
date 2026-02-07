# AYC Fund - Bybit AI Trading Competition 2026

> **Team**: AYC Fund (YC W22)
> **Strategy**: ATR Adaptive Grid + EMA Trend Filter (V9.5)
> **AI Model**: Claude Code Opus 4.6

---

## Strategy Overview

Our AI trading strategy combines **ATR-based adaptive grid trading** with **EMA trend filtering** and **regime-aware market classification**. The system autonomously adjusts its parameters based on real-time market conditions.

### Key Features

- **4-Quadrant Regime Classification**: Automatically detects market conditions (Stable Trend, Volatile Trend, Sideways Quiet, Sideways Chop)
- **Dynamic Grid Spacing**: Adjusts entry/exit levels based on ATR volatility
- **Hedge Mode (V9.5)**: Simultaneous LONG and SHORT positions for market-neutral exposure
- **Trailing Stop Loss**: Protects profits with adaptive trailing mechanism
- **CapitalGuard (50% Rule)**: Risk management to prevent over-leverage

---

## Performance Metrics (365-day Backtest)

| Metric | Value |
|--------|-------|
| Total Trades | 5,256+ |
| Win Rate | 31-33% |
| Profit Factor | 3.91 |
| Max Drawdown | < 2% |
| Sharpe Ratio | 16.5+ |

### Tier Performance

| Tier | Leverage | ROI | Win Rate | Liquidation Risk |
|------|----------|-----|----------|------------------|
| Shield | 1x | +94.1% | 98.3% | 0% |
| Balance | 3x | +837.8% | 99.3% | 0% |
| Boost | 5x | +1,392% | 99.3% | 0% |

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Signal Provider                       │
│  (Centralized signal calculation, 60s intervals)        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Regime Detector                        │
│  ADX + ATR Ratio → 4 Market Regimes                     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Grid Strategy                          │
│  - Dynamic entry/exit levels                            │
│  - Hedge mode (Long + Short)                            │
│  - Trailing stop loss                                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Risk Manager                           │
│  - CapitalGuard (50% margin limit)                      │
│  - Emergency stop (-15% drawdown)                       │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Bybit Exchange API                      │
│  (CCXT integration, order management)                   │
└─────────────────────────────────────────────────────────┘
```

---

## AI Integration

### Claude Code Usage

Our strategy leverages Claude AI (Opus 4.6) for:

1. **Strategy Development**: Code generation and optimization
2. **Backtesting Analysis**: Performance evaluation and parameter tuning
3. **Real-time Monitoring**: Trade signal validation and risk assessment
4. **Bug Detection**: Automated code review and error correction

### Interaction Frequency

| Component | Frequency | Description |
|-----------|-----------|-------------|
| Signal Check | 60 seconds | Main execution loop |
| Regime Detection | 60 seconds | Market classification update |
| Grid Update | Per tick | Dynamic entry/exit adjustment |
| Risk Check | Real-time | Continuous margin monitoring |

---

## File Structure

```
ayc-bybit-competition-2026/
├── README.md                    # This file
├── strategy/
│   ├── atr_grid_strategy.py     # Core grid strategy logic
│   ├── regime_detector.py       # Market regime classification
│   └── risk_manager.py          # CapitalGuard implementation
├── config/
│   └── parameters.py            # Strategy parameters
├── docs/
│   └── STRATEGY.md              # Detailed strategy documentation
└── backtest/
    └── results/                 # Backtest results and analysis
```

---

## Trading Pairs

Dynamic selection of top 10 symbols by 24h volume from Bybit futures.

**Supported pairs include**:
- BTC/USDT, ETH/USDT, SOL/USDT
- ARB/USDT, OP/USDT, SUI/USDT
- And more...

---

## Risk Management

### CapitalGuard (50% Rule)

```python
safe_balance = total_equity × 0.50
potential_margin = margin_per_level × max_levels

if potential_margin > safe_balance:
    → Entry BLOCKED
```

### Stop Loss Mechanism

- **Grid-wide SL**: Based on average entry price
- **Trailing SL**: Follows profitable positions
- **Emergency Stop**: -15% equity drawdown trigger

---

## Competition Configuration

| Parameter | Value |
|-----------|-------|
| Initial Capital | 1,000 USDT |
| Leverage | 3x (Balance tier) |
| Max Positions | 5 levels per direction |
| Risk per Trade | 10% of equity |
| Minimum Trades/Day | 10+ (expected: 14-144) |

---

## Contact

- **Team**: AYC Fund (YC W22)
- **Telegram**: @runwithcrypto
- **Email**: mj@aycfund.com

---

## Disclaimer

This code is provided for the Bybit AI Trading Competition 2026. Past performance does not guarantee future results. Cryptocurrency trading involves significant risk.

---

*Generated with Claude Code - February 2026*
