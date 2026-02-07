"""
ATR Adaptive Grid Strategy (V9.5)

Core trading logic for Bybit AI Trading Competition 2026.
Implements ATR-based grid trading with EMA trend filter and regime detection.

Author: AYC Fund (YC W22)
Version: 9.5

Note: Actual parameters are loaded from production configuration.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class GridDirection(str, Enum):
    """Grid direction."""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"
    BOTH = "both"  # Hedge Mode support


class MarketRegime(str, Enum):
    """Market regime classification."""
    STABLE_TREND = "stable_trend"
    VOLATILE_TREND = "volatile_trend"
    SIDEWAYS_QUIET = "sideways_quiet"
    SIDEWAYS_CHOP = "sideways_chop"
    UNKNOWN = "unknown"


@dataclass
class RegimeConfig:
    """Configuration for each market regime."""
    base_spacing_pct: float
    tp_mult: float
    sl_drawdown: float
    max_levels: int
    volatility_threshold: float
    ai_filter_strict: bool

    @classmethod
    def from_production_config(cls, regime: str) -> "RegimeConfig":
        """
        Load regime configuration from production environment.

        Production parameters are not included in public repository
        for competitive advantage protection.
        """
        # Production config loaded from secure environment
        config = _load_regime_config(regime)
        return cls(**config)


def _load_regime_config(regime: str) -> Dict:
    """
    Load regime-specific parameters from production configuration.

    This function loads actual trading parameters from:
    - Environment variables
    - Secure configuration service
    - Encrypted parameter store

    Parameters are optimized through extensive backtesting
    and are not disclosed in public repository.
    """
    # Placeholder - actual values loaded from production config
    return {
        "base_spacing_pct": float(os.getenv(f"REGIME_{regime.upper()}_SPACING", "0")),
        "tp_mult": float(os.getenv(f"REGIME_{regime.upper()}_TP_MULT", "1")),
        "sl_drawdown": float(os.getenv(f"REGIME_{regime.upper()}_SL", "0")),
        "max_levels": int(os.getenv(f"REGIME_{regime.upper()}_LEVELS", "0")),
        "volatility_threshold": float(os.getenv(f"REGIME_{regime.upper()}_VOL", "1")),
        "ai_filter_strict": os.getenv(f"REGIME_{regime.upper()}_STRICT", "false").lower() == "true",
    }


# Regime configurations - actual values loaded from production environment
REGIME_CONFIGS: Dict[MarketRegime, RegimeConfig] = {}


def initialize_regime_configs():
    """Initialize regime configurations from production environment."""
    global REGIME_CONFIGS
    for regime in MarketRegime:
        if regime != MarketRegime.UNKNOWN:
            try:
                REGIME_CONFIGS[regime] = RegimeConfig.from_production_config(regime.value)
            except Exception:
                # Default placeholder config
                REGIME_CONFIGS[regime] = RegimeConfig(
                    base_spacing_pct=0,
                    tp_mult=1,
                    sl_drawdown=0,
                    max_levels=0,
                    volatility_threshold=1,
                    ai_filter_strict=False
                )


@dataclass
class GridLevel:
    """A single grid level."""
    level: int
    direction: GridDirection
    entry_price: float
    tp_price: float
    quantity: float
    order_id: Optional[str] = None
    tp_order_id: Optional[str] = None
    status: str = "pending"
    entry_time: Optional[str] = None
    fill_time: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "level": self.level,
            "direction": self.direction.value,
            "entry_price": self.entry_price,
            "tp_price": self.tp_price,
            "quantity": self.quantity,
            "order_id": self.order_id,
            "tp_order_id": self.tp_order_id,
            "status": self.status,
            "entry_time": self.entry_time,
            "fill_time": self.fill_time
        }


@dataclass
class GridState:
    """Persistent state of a running grid."""
    symbol: str
    direction: GridDirection = GridDirection.NEUTRAL
    current_atr: float = 0.0
    current_ema: float = 0.0
    spacing: float = 0.0
    levels: List[GridLevel] = field(default_factory=list)
    sl_price: Optional[float] = None
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    sl_drawdown: Optional[float] = None
    last_update: str = ""

    # V9.5 Independent SL for Hedge Mode
    long_sl_price: Optional[float] = None
    short_sl_price: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "current_atr": self.current_atr,
            "current_ema": self.current_ema,
            "spacing": self.spacing,
            "levels": [l.to_dict() for l in self.levels],
            "sl_price": self.sl_price,
            "highest_price": self.highest_price,
            "lowest_price": self.lowest_price,
            "sl_drawdown": self.sl_drawdown,
            "last_update": self.last_update,
            "long_sl_price": self.long_sl_price,
            "short_sl_price": self.short_sl_price,
        }


class RegimeDetector:
    """Detects market regime based on ADX and ATR ratio."""

    def __init__(self, window_short: int = None, window_long: int = None):
        # Load from production config
        self.window_short = window_short or int(os.getenv("ATR_WINDOW_SHORT", "14"))
        self.window_long = window_long or int(os.getenv("ATR_WINDOW_LONG", "50"))
        self.adx_threshold = float(os.getenv("ADX_THRESHOLD", "0"))
        self.atr_vol_threshold = float(os.getenv("ATR_VOL_THRESHOLD", "0"))

    def calculate_adx(self, df: pd.DataFrame) -> float:
        """Calculate Average Directional Index."""
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Smoothed values
        atr = pd.Series(tr).ewm(span=self.window_short, adjust=False).mean()
        plus_di = 100 * pd.Series(plus_dm).ewm(span=self.window_short, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).ewm(span=self.window_short, adjust=False).mean() / atr

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=self.window_short, adjust=False).mean()

        return float(adx.iloc[-1])

    def calculate_atr_ratio(self, df: pd.DataFrame) -> float:
        """Calculate ATR ratio (current ATR / MA of ATR)."""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(span=self.window_short, adjust=False).mean()
        atr_ma = atr.rolling(window=self.window_long).mean()

        current_atr = atr.iloc[-1]
        avg_atr = atr_ma.iloc[-1]

        if avg_atr > 0:
            return current_atr / avg_atr
        return 1.0

    def detect_regime(self, df: pd.DataFrame) -> Tuple[MarketRegime, float, float]:
        """
        Detect market regime based on ADX and ATR ratio.

        Returns:
            Tuple of (regime, adx, atr_ratio)
        """
        if len(df) < self.window_long:
            return MarketRegime.UNKNOWN, 0.0, 1.0

        adx = self.calculate_adx(df)
        atr_ratio = self.calculate_atr_ratio(df)

        # 4-Quadrant Classification using production thresholds
        if adx > self.adx_threshold:
            if atr_ratio < self.atr_vol_threshold:
                regime = MarketRegime.STABLE_TREND
            else:
                regime = MarketRegime.VOLATILE_TREND
        else:
            if atr_ratio < self.atr_vol_threshold:
                regime = MarketRegime.SIDEWAYS_QUIET
            else:
                regime = MarketRegime.SIDEWAYS_CHOP

        return regime, adx, atr_ratio


class ATRGridStrategy:
    """
    ATR Adaptive Grid Strategy with EMA Trend Filter.

    Core logic for V9.5 trading system with:
    - Regime-aware parameter adaptation
    - Hedge mode (simultaneous Long/Short)
    - Trailing stop loss

    Note: Production parameters loaded from secure configuration.
    """

    def __init__(
        self,
        ema_period: int = None,
        atr_period: int = None,
        max_levels: int = None,
    ):
        # Load from production config
        self.ema_period = ema_period or int(os.getenv("EMA_PERIOD", "200"))
        self.atr_period = atr_period or int(os.getenv("ATR_PERIOD", "14"))
        self.max_levels = max_levels or int(os.getenv("MAX_LEVELS", "0"))

        # Spacing multipliers from production config
        self.spacing_low = float(os.getenv("SPACING_LOW_MULT", "0"))
        self.spacing_normal = float(os.getenv("SPACING_NORMAL_MULT", "0"))
        self.spacing_high = float(os.getenv("SPACING_HIGH_MULT", "0"))
        self.vol_low_threshold = float(os.getenv("VOL_LOW_THRESHOLD", "0"))
        self.vol_high_threshold = float(os.getenv("VOL_HIGH_THRESHOLD", "0"))
        self.sl_atr_mult = float(os.getenv("SL_ATR_MULT", "0"))

        # Regime detector
        self.regime_detector = RegimeDetector()

    def calculate_indicators(self, df: pd.DataFrame) -> Tuple[float, float]:
        """Calculate EMA and ATR from OHLCV data."""
        if len(df) < self.ema_period:
            return 0.0, 0.0

        # EMA
        ema_series = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        current_ema = ema_series.iloc[-1]

        # ATR
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_series = tr.ewm(span=self.atr_period, adjust=False).mean()
        current_atr = atr_series.iloc[-1]

        return float(current_ema), float(current_atr)

    def get_regime_config(self, regime: MarketRegime) -> RegimeConfig:
        """Get configuration for a specific market regime."""
        if not REGIME_CONFIGS:
            initialize_regime_configs()
        return REGIME_CONFIGS.get(regime, REGIME_CONFIGS.get(MarketRegime.UNKNOWN))

    def should_skip_entry(
        self,
        regime: MarketRegime,
        adx: float,
        is_bearish: bool,
        volatility_ratio: float
    ) -> Tuple[bool, str]:
        """
        Determine if entry should be skipped based on market conditions.

        Logic uses production-configured thresholds for AI filtering.
        """
        # Skip conditions based on production config
        config = self.get_regime_config(regime)
        if config is None:
            return False, ""

        vol_threshold = config.volatility_threshold
        ai_filter_strict = config.ai_filter_strict

        if ai_filter_strict and is_bearish and volatility_ratio > vol_threshold:
            return True, f"AI Filter ({regime.value})"

        return False, ""

    def calculate_next_entry_price(
        self,
        direction: GridDirection,
        current_price: float,
        current_atr: float,
        regime: Optional[MarketRegime] = None,
    ) -> float:
        """
        Calculate the next entry price for dynamic DCA.

        V9.5 Logic:
        - Entry is always relative to CURRENT price (Trailing Entry)
        - Long Entry = Current * (1 - Spacing)
        - Short Entry = Current * (1 + Spacing)
        """
        # Get spacing from regime config
        if regime:
            config = self.get_regime_config(regime)
            base_spacing_pct = config.base_spacing_pct if config else 0
        else:
            base_spacing_pct = float(os.getenv("DEFAULT_SPACING_PCT", "0"))

        # Calculate spacing using proprietary formula
        spacing = self._calculate_adaptive_spacing(current_price, current_atr, base_spacing_pct, regime)

        if direction == GridDirection.LONG:
            return current_price - spacing
        else:  # SHORT
            return current_price + spacing

    def _calculate_adaptive_spacing(
        self,
        current_price: float,
        current_atr: float,
        base_spacing_pct: float,
        regime: Optional[MarketRegime] = None,
    ) -> float:
        """
        Calculate adaptive spacing based on ATR and regime.

        Proprietary formula - actual implementation in production config.
        """
        # Simplified placeholder - actual formula in production
        min_spacing = current_price * base_spacing_pct
        atr_spacing = current_atr * self.sl_atr_mult
        return max(atr_spacing, min_spacing)

    def calculate_tp_price(
        self,
        direction: GridDirection,
        entry_price: float,
        spacing: float,
        regime: Optional[MarketRegime] = None,
    ) -> float:
        """Calculate take profit price for a grid level."""
        if regime:
            config = self.get_regime_config(regime)
            tp_mult = config.tp_mult if config else 1.0
        else:
            tp_mult = float(os.getenv("DEFAULT_TP_MULT", "1"))

        if direction == GridDirection.LONG:
            return entry_price + (spacing * tp_mult)
        else:  # SHORT
            return entry_price - (spacing * tp_mult)

    def calculate_sl_price(
        self,
        direction: GridDirection,
        avg_entry_price: float,
        regime: Optional[MarketRegime] = None,
    ) -> float:
        """Calculate stop loss price based on regime configuration."""
        if regime:
            config = self.get_regime_config(regime)
            sl_drawdown = config.sl_drawdown if config else 0
        else:
            sl_drawdown = float(os.getenv("DEFAULT_SL_DRAWDOWN", "0"))

        if direction == GridDirection.LONG:
            return avg_entry_price * (1 - sl_drawdown)
        else:  # SHORT
            return avg_entry_price * (1 + sl_drawdown)

    def update_trailing_sl(
        self,
        direction: GridDirection,
        current_price: float,
        current_sl: float,
        highest_price: float,
        lowest_price: float,
        sl_drawdown: float,
    ) -> Tuple[float, float, float]:
        """
        Update trailing stop loss based on price movement.

        Returns:
            Tuple of (new_sl, new_highest, new_lowest)
        """
        new_highest = highest_price
        new_lowest = lowest_price
        new_sl = current_sl

        if direction == GridDirection.LONG:
            if current_price > highest_price:
                new_highest = current_price
            trailing_sl = new_highest * (1 - sl_drawdown)
            if trailing_sl > current_sl:
                new_sl = trailing_sl

        else:  # SHORT
            if current_price < lowest_price:
                new_lowest = current_price
            trailing_sl = new_lowest * (1 + sl_drawdown)
            if trailing_sl < current_sl:
                new_sl = trailing_sl

        return new_sl, new_highest, new_lowest

    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
    ) -> Dict:
        """
        Generate trading signal from OHLCV data.

        Returns:
            Dict with signal information
        """
        ema, atr = self.calculate_indicators(df)
        regime, adx, atr_ratio = self.regime_detector.detect_regime(df)

        is_bullish = current_price > ema
        is_bearish = current_price < ema

        skip_entry, skip_reason = self.should_skip_entry(
            regime, adx, is_bearish, atr_ratio
        )

        if is_bullish:
            direction = GridDirection.LONG
        elif is_bearish:
            direction = GridDirection.SHORT
        else:
            direction = GridDirection.NEUTRAL

        return {
            "current_price": current_price,
            "ema": ema,
            "atr": atr,
            "adx": adx,
            "atr_ratio": atr_ratio,
            "regime": regime,
            "direction": direction,
            "is_bullish": is_bullish,
            "is_bearish": is_bearish,
            "skip_entry": skip_entry,
            "skip_reason": skip_reason,
        }


# Example usage
if __name__ == "__main__":
    print("ATR Grid Strategy V9.5")
    print("=" * 50)
    print("\nNote: Production parameters loaded from environment.")
    print("This public repository contains strategy structure only.")
    print("\nFor competition evaluation, contact: @runwithcrypto")
