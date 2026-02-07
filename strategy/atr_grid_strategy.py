"""
ATR Adaptive Grid Strategy (V9.5)

Core trading logic for Bybit AI Trading Competition 2026.
Implements ATR-based grid trading with EMA trend filter and regime detection.

Author: AYC Fund (YC W22)
Version: 9.5
"""

import logging
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
    STABLE_TREND = "stable_trend"      # ADX > 25, ATR Ratio < 1.2
    VOLATILE_TREND = "volatile_trend"  # ADX > 25, ATR Ratio >= 1.2
    SIDEWAYS_QUIET = "sideways_quiet"  # ADX <= 25, ATR Ratio < 1.2
    SIDEWAYS_CHOP = "sideways_chop"    # ADX <= 25, ATR Ratio >= 1.2
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


# Regime-specific configurations
REGIME_CONFIGS = {
    MarketRegime.STABLE_TREND: RegimeConfig(
        base_spacing_pct=0.010,   # 1.0%
        tp_mult=1.2,
        sl_drawdown=0.08,        # 8%
        max_levels=5,
        volatility_threshold=1.5,
        ai_filter_strict=False
    ),
    MarketRegime.VOLATILE_TREND: RegimeConfig(
        base_spacing_pct=0.015,   # 1.5%
        tp_mult=1.0,
        sl_drawdown=0.04,        # 4%
        max_levels=5,
        volatility_threshold=1.2,
        ai_filter_strict=True
    ),
    MarketRegime.SIDEWAYS_QUIET: RegimeConfig(
        base_spacing_pct=0.005,   # 0.5%
        tp_mult=1.1,
        sl_drawdown=0.05,        # 5%
        max_levels=5,
        volatility_threshold=1.0,
        ai_filter_strict=False
    ),
    MarketRegime.SIDEWAYS_CHOP: RegimeConfig(
        base_spacing_pct=0.020,   # 2.0%
        tp_mult=0.8,
        sl_drawdown=0.03,        # 3%
        max_levels=3,            # Reduced levels for choppy market
        volatility_threshold=0.8,
        ai_filter_strict=True
    ),
    MarketRegime.UNKNOWN: RegimeConfig(
        base_spacing_pct=0.010,
        tp_mult=1.0,
        sl_drawdown=0.05,
        max_levels=5,
        volatility_threshold=1.0,
        ai_filter_strict=False
    ),
}


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
    status: str = "pending"  # pending, active, filled, closed
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

    def __init__(self, window_short: int = 14, window_long: int = 50):
        self.window_short = window_short
        self.window_long = window_long
        self.adx_threshold = 25.0
        self.atr_vol_threshold = 1.2

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

        # 4-Quadrant Classification
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
    """

    def __init__(
        self,
        ema_period: int = 200,
        atr_period: int = 14,
        max_levels: int = 5,
    ):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.max_levels = max_levels

        # Default spacing multipliers
        self.spacing_low = 0.6
        self.spacing_normal = 1.0
        self.spacing_high = 1.5
        self.vol_low_threshold = 0.8
        self.vol_high_threshold = 1.5
        self.sl_atr_mult = 1.5

        # Regime detector
        self.regime_detector = RegimeDetector(window_short=14, window_long=50)

    def calculate_indicators(self, df: pd.DataFrame) -> Tuple[float, float]:
        """Calculate EMA and ATR from OHLCV data."""
        if len(df) < self.ema_period:
            return 0.0, 0.0

        # EMA 200
        ema_series = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        current_ema = ema_series.iloc[-1]

        # ATR 14
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
        return REGIME_CONFIGS.get(regime, REGIME_CONFIGS[MarketRegime.UNKNOWN])

    def should_skip_entry(
        self,
        regime: MarketRegime,
        adx: float,
        is_bearish: bool,
        volatility_ratio: float
    ) -> Tuple[bool, str]:
        """
        Determine if entry should be skipped based on market conditions.

        Only skips in strong downtrend conditions:
        - ADX > 25 (strong trend)
        - Price below EMA (bearish)
        - VOLATILE_TREND regime
        """
        # Skip in strong bearish volatile trend
        if adx > 25 and is_bearish and regime == MarketRegime.VOLATILE_TREND:
            return True, f"Strong downtrend (ADX={adx:.1f}, Bearish, Volatile)"

        # Check regime-specific volatility threshold
        config = self.get_regime_config(regime)
        vol_threshold = config.volatility_threshold
        ai_filter_strict = config.ai_filter_strict

        if ai_filter_strict and is_bearish and volatility_ratio > vol_threshold:
            return True, f"AI Filter ({regime.value}): vol={volatility_ratio:.3f} > {vol_threshold}"

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
            base_spacing_pct = config.base_spacing_pct
            aggressive_mode = (regime == MarketRegime.STABLE_TREND)
        else:
            base_spacing_pct = 0.010  # Default 1%
            aggressive_mode = False

        # Calculate spacing
        atr_spacing = current_atr * (0.8 if aggressive_mode else 1.5)
        min_spacing = current_price * base_spacing_pct
        spacing = max(atr_spacing, min_spacing)

        if direction == GridDirection.LONG:
            return current_price - spacing
        else:  # SHORT
            return current_price + spacing

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
            tp_mult = config.tp_mult
        else:
            tp_mult = 1.0

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
            sl_drawdown = config.sl_drawdown
        else:
            sl_drawdown = 0.05  # Default 5%

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
            # Update peak
            if current_price > highest_price:
                new_highest = current_price

            # Calculate trailing SL
            trailing_sl = new_highest * (1 - sl_drawdown)
            if trailing_sl > current_sl:
                new_sl = trailing_sl

        else:  # SHORT
            # Update trough
            if current_price < lowest_price:
                new_lowest = current_price

            # Calculate trailing SL (for short, SL is above price)
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
            Dict with signal information including:
            - ema, atr, adx, atr_ratio
            - regime
            - direction
            - skip_entry (bool)
            - skip_reason (str)
        """
        ema, atr = self.calculate_indicators(df)
        regime, adx, atr_ratio = self.regime_detector.detect_regime(df)

        is_bullish = current_price > ema
        is_bearish = current_price < ema

        # Check if entry should be skipped
        skip_entry, skip_reason = self.should_skip_entry(
            regime, adx, is_bearish, atr_ratio
        )

        # Determine direction
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
    # Initialize strategy
    strategy = ATRGridStrategy(
        ema_period=200,
        atr_period=14,
        max_levels=5,
    )

    # Example with sample data
    print("ATR Grid Strategy V9.5 initialized")
    print(f"EMA Period: {strategy.ema_period}")
    print(f"ATR Period: {strategy.atr_period}")
    print(f"Max Levels: {strategy.max_levels}")

    # Show regime configurations
    print("\nRegime Configurations:")
    for regime, config in REGIME_CONFIGS.items():
        print(f"  {regime.value}: spacing={config.base_spacing_pct:.1%}, "
              f"tp_mult={config.tp_mult}, sl={config.sl_drawdown:.0%}, "
              f"levels={config.max_levels}")
