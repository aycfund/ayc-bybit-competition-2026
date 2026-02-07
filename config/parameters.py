"""
Strategy Parameters Configuration

Configuration loader for ATR Grid Strategy V9.5.
Actual parameter values are loaded from production environment.

Author: AYC Fund (YC W22)
Version: 9.5

Note: This file contains parameter structure only.
      Production values are loaded from secure environment.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class TradingTier(str, Enum):
    """Service tier configuration."""
    SHIELD = "shield"      # Conservative
    BALANCE = "balance"    # Standard
    BOOST = "boost"        # Aggressive


@dataclass
class TierConfig:
    """Configuration for each trading tier."""
    name: str
    leverage: int
    capital_pct: float
    max_positions: int
    description: str

    @classmethod
    def from_production(cls, tier: str) -> "TierConfig":
        """Load tier configuration from production environment."""
        return cls(
            name=tier.capitalize(),
            leverage=int(os.getenv(f"TIER_{tier.upper()}_LEVERAGE", "0")),
            capital_pct=float(os.getenv(f"TIER_{tier.upper()}_CAPITAL_PCT", "0")),
            max_positions=int(os.getenv(f"TIER_{tier.upper()}_MAX_POS", "0")),
            description=f"{tier.capitalize()} tier configuration",
        )


# Tier Configurations - loaded from production environment
TIER_CONFIGS: Dict[TradingTier, TierConfig] = {}


def _load_tier_configs():
    """Load tier configurations from production environment."""
    global TIER_CONFIGS
    for tier in TradingTier:
        TIER_CONFIGS[tier] = TierConfig.from_production(tier.value)


@dataclass
class StrategyParameters:
    """
    Complete strategy parameters.

    Note: All values are loaded from production configuration.
    Default values shown here are placeholders only.
    """

    # Indicator Settings
    ema_period: int = 0
    atr_period: int = 0
    adx_threshold: float = 0.0
    atr_vol_threshold: float = 0.0

    # Grid Settings
    max_levels: int = 0
    spacing_low_mult: float = 0.0
    spacing_normal_mult: float = 0.0
    spacing_high_mult: float = 0.0

    # Volatility Thresholds
    vol_low_threshold: float = 0.0
    vol_high_threshold: float = 0.0

    # Stop Loss Settings
    sl_atr_mult: float = 0.0
    trailing_enabled: bool = True

    # Risk Management
    max_margin_ratio: float = 0.0
    emergency_drawdown: float = 0.0

    # Execution Settings
    execution_interval: int = 60
    timeframe: str = "1h"

    @classmethod
    def from_production(cls) -> "StrategyParameters":
        """Load all parameters from production environment."""
        return cls(
            ema_period=int(os.getenv("EMA_PERIOD", "0")),
            atr_period=int(os.getenv("ATR_PERIOD", "0")),
            adx_threshold=float(os.getenv("ADX_THRESHOLD", "0")),
            atr_vol_threshold=float(os.getenv("ATR_VOL_THRESHOLD", "0")),
            max_levels=int(os.getenv("MAX_LEVELS", "0")),
            spacing_low_mult=float(os.getenv("SPACING_LOW_MULT", "0")),
            spacing_normal_mult=float(os.getenv("SPACING_NORMAL_MULT", "0")),
            spacing_high_mult=float(os.getenv("SPACING_HIGH_MULT", "0")),
            vol_low_threshold=float(os.getenv("VOL_LOW_THRESHOLD", "0")),
            vol_high_threshold=float(os.getenv("VOL_HIGH_THRESHOLD", "0")),
            sl_atr_mult=float(os.getenv("SL_ATR_MULT", "0")),
            trailing_enabled=os.getenv("TRAILING_ENABLED", "true").lower() == "true",
            max_margin_ratio=float(os.getenv("MAX_MARGIN_RATIO", "0")),
            emergency_drawdown=float(os.getenv("EMERGENCY_DRAWDOWN", "0")),
            execution_interval=int(os.getenv("EXECUTION_INTERVAL", "60")),
            timeframe=os.getenv("TIMEFRAME", "1h"),
        )


# Regime-specific Parameter Structure
REGIME_PARAMETERS = {
    "stable_trend": {
        "base_spacing_pct": "PRODUCTION_CONFIG",
        "tp_mult": "PRODUCTION_CONFIG",
        "sl_drawdown": "PRODUCTION_CONFIG",
        "max_levels": "PRODUCTION_CONFIG",
    },
    "volatile_trend": {
        "base_spacing_pct": "PRODUCTION_CONFIG",
        "tp_mult": "PRODUCTION_CONFIG",
        "sl_drawdown": "PRODUCTION_CONFIG",
        "max_levels": "PRODUCTION_CONFIG",
    },
    "sideways_quiet": {
        "base_spacing_pct": "PRODUCTION_CONFIG",
        "tp_mult": "PRODUCTION_CONFIG",
        "sl_drawdown": "PRODUCTION_CONFIG",
        "max_levels": "PRODUCTION_CONFIG",
    },
    "sideways_chop": {
        "base_spacing_pct": "PRODUCTION_CONFIG",
        "tp_mult": "PRODUCTION_CONFIG",
        "sl_drawdown": "PRODUCTION_CONFIG",
        "max_levels": "PRODUCTION_CONFIG",
    },
}


# Cost Model Structure
COST_MODEL = {
    "fee_rate": "PRODUCTION_CONFIG",
    "slippage_rate": "PRODUCTION_CONFIG",
    "funding_rate": "PRODUCTION_CONFIG",
}


# Symbol Configuration
SAFE_SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    # Additional symbols loaded from production config
]


# Competition Configuration
COMPETITION_CONFIG = {
    "initial_capital": 1000,       # USDT (public requirement)
    "tier": TradingTier.BALANCE,
    "num_symbols": 10,             # Top 10 by volume
    "min_trades_per_day": 10,      # Competition requirement
    "leverage_limit": 15,          # Competition limit
}


def get_parameters(tier: TradingTier = TradingTier.BALANCE) -> Dict:
    """
    Get complete parameters for a trading tier.

    Note: Production values loaded from secure environment.
    """
    if not TIER_CONFIGS:
        _load_tier_configs()

    tier_config = TIER_CONFIGS.get(tier)
    base_params = StrategyParameters.from_production()

    return {
        # Tier settings
        "tier": tier.value,
        "leverage": tier_config.leverage if tier_config else 0,
        "capital_pct": tier_config.capital_pct if tier_config else 0,
        "max_positions": tier_config.max_positions if tier_config else 0,

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
    print("\nNote: Production parameters loaded from environment.")
    print("This public repository contains parameter structure only.")
    print("\nFor competition evaluation, contact: @runwithcrypto")
