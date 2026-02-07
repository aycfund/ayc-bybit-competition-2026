"""
Strategy Parameters Configuration

All configurable parameters for the ATR Grid Strategy V9.5.

Author: AYC Fund (YC W22)
Version: 9.5
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class TradingTier(str, Enum):
    """Service tier configuration."""
    SHIELD = "shield"      # Conservative: 1x leverage
    BALANCE = "balance"    # Standard: 3x leverage
    BOOST = "boost"        # Aggressive: 5x leverage


@dataclass
class TierConfig:
    """Configuration for each trading tier."""
    name: str
    leverage: int
    capital_pct: float
    max_positions: int
    description: str


# Tier Configurations
TIER_CONFIGS: Dict[TradingTier, TierConfig] = {
    TradingTier.SHIELD: TierConfig(
        name="Shield",
        leverage=1,
        capital_pct=0.05,      # 5% of equity
        max_positions=5,
        description="Conservative tier for capital preservation",
    ),
    TradingTier.BALANCE: TierConfig(
        name="Balance",
        leverage=3,
        capital_pct=0.25,      # 25% of equity
        max_positions=5,
        description="Balanced tier for steady growth",
    ),
    TradingTier.BOOST: TierConfig(
        name="Boost",
        leverage=5,
        capital_pct=0.30,      # 30% of equity
        max_positions=5,
        description="Aggressive tier for maximum returns",
    ),
}


@dataclass
class StrategyParameters:
    """Complete strategy parameters."""

    # Indicator Settings
    ema_period: int = 200          # EMA period for trend detection
    atr_period: int = 14           # ATR period for volatility
    adx_threshold: float = 25.0    # ADX threshold for trend strength
    atr_vol_threshold: float = 1.2  # ATR ratio threshold for volatility

    # Grid Settings
    max_levels: int = 5            # Maximum grid levels
    spacing_low_mult: float = 0.6  # Spacing multiplier for low volatility
    spacing_normal_mult: float = 1.0  # Spacing multiplier for normal volatility
    spacing_high_mult: float = 1.5  # Spacing multiplier for high volatility

    # Volatility Thresholds
    vol_low_threshold: float = 0.8   # ATR ratio below = low volatility
    vol_high_threshold: float = 1.5  # ATR ratio above = high volatility

    # Stop Loss Settings
    sl_atr_mult: float = 1.5        # SL distance as ATR multiplier
    trailing_enabled: bool = True   # Enable trailing stop loss

    # Risk Management
    max_margin_ratio: float = 0.50   # CapitalGuard 50% rule
    emergency_drawdown: float = 0.15  # Emergency stop at 15% drawdown

    # Execution Settings
    execution_interval: int = 60     # Seconds between checks
    timeframe: str = "1h"            # Candle timeframe for indicators


# Regime-specific Parameter Overrides
REGIME_PARAMETERS = {
    "stable_trend": {
        "base_spacing_pct": 0.010,  # 1.0%
        "tp_mult": 1.2,
        "sl_drawdown": 0.08,       # 8%
        "max_levels": 5,
    },
    "volatile_trend": {
        "base_spacing_pct": 0.015,  # 1.5%
        "tp_mult": 1.0,
        "sl_drawdown": 0.04,       # 4%
        "max_levels": 5,
    },
    "sideways_quiet": {
        "base_spacing_pct": 0.005,  # 0.5%
        "tp_mult": 1.1,
        "sl_drawdown": 0.05,       # 5%
        "max_levels": 5,
    },
    "sideways_chop": {
        "base_spacing_pct": 0.020,  # 2.0%
        "tp_mult": 0.8,
        "sl_drawdown": 0.03,       # 3%
        "max_levels": 3,           # Reduced for choppy market
    },
}


# Cost Model Parameters
COST_MODEL = {
    "fee_rate": 0.0005,        # 0.05% trading fee
    "slippage_rate": 0.0003,   # 0.03% slippage
    "funding_rate": 0.0001,    # 0.01% per 8 hours
}


# Symbol Configuration
SAFE_SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "ARB/USDT:USDT",
    "OP/USDT:USDT",
    "SUI/USDT:USDT",
    "NEAR/USDT:USDT",
    "INJ/USDT:USDT",
    "UNI/USDT:USDT",
    "ADA/USDT:USDT",
]


# Competition Configuration
COMPETITION_CONFIG = {
    "initial_capital": 1000,       # USDT
    "tier": TradingTier.BALANCE,   # 3x leverage
    "num_symbols": 10,             # Top 10 by volume
    "min_trades_per_day": 10,      # Competition requirement
    "leverage_limit": 15,          # Competition limit
}


def get_parameters(tier: TradingTier = TradingTier.BALANCE) -> Dict:
    """Get complete parameters for a trading tier."""
    tier_config = TIER_CONFIGS[tier]
    base_params = StrategyParameters()

    return {
        # Tier settings
        "tier": tier.value,
        "leverage": tier_config.leverage,
        "capital_pct": tier_config.capital_pct,
        "max_positions": tier_config.max_positions,

        # Indicator settings
        "ema_period": base_params.ema_period,
        "atr_period": base_params.atr_period,
        "adx_threshold": base_params.adx_threshold,
        "atr_vol_threshold": base_params.atr_vol_threshold,

        # Grid settings
        "max_levels": base_params.max_levels,
        "spacing_low_mult": base_params.spacing_low_mult,
        "spacing_normal_mult": base_params.spacing_normal_mult,
        "spacing_high_mult": base_params.spacing_high_mult,

        # Stop loss
        "sl_atr_mult": base_params.sl_atr_mult,
        "trailing_enabled": base_params.trailing_enabled,

        # Risk management
        "max_margin_ratio": base_params.max_margin_ratio,
        "emergency_drawdown": base_params.emergency_drawdown,

        # Execution
        "execution_interval": base_params.execution_interval,
        "timeframe": base_params.timeframe,

        # Costs
        "cost_model": COST_MODEL,

        # Regime parameters
        "regime_parameters": REGIME_PARAMETERS,
    }


# Example usage
if __name__ == "__main__":
    print("Strategy Parameters V9.5")
    print("=" * 50)

    for tier in TradingTier:
        config = TIER_CONFIGS[tier]
        print(f"\n{config.name} Tier:")
        print(f"  Leverage: {config.leverage}x")
        print(f"  Capital %: {config.capital_pct:.0%}")
        print(f"  Max Positions: {config.max_positions}")
        print(f"  Description: {config.description}")

    print("\n" + "=" * 50)
    print("Competition Configuration:")
    for key, value in COMPETITION_CONFIG.items():
        print(f"  {key}: {value}")
