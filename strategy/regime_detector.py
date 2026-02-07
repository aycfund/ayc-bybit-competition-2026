"""
Market Regime Detector

Classifies market conditions using ADX and ATR ratio for adaptive trading.

Author: AYC Fund (YC W22)
Version: 9.5
"""

import pandas as pd
import numpy as np
from enum import Enum
from typing import Tuple, Optional
from dataclasses import dataclass


class MarketRegime(str, Enum):
    """
    4-Quadrant Market Regime Classification.

    Based on two dimensions:
    1. Trend Strength (ADX > 25 = Trending, ADX <= 25 = Sideways)
    2. Volatility (ATR Ratio > 1.2 = High, ATR Ratio <= 1.2 = Low)

    Quadrants:
    - STABLE_TREND: Strong trend, low volatility (best for grid trading)
    - VOLATILE_TREND: Strong trend, high volatility (cautious trading)
    - SIDEWAYS_QUIET: No trend, low volatility (range trading)
    - SIDEWAYS_CHOP: No trend, high volatility (reduce exposure)
    """
    STABLE_TREND = "stable_trend"
    VOLATILE_TREND = "volatile_trend"
    SIDEWAYS_QUIET = "sideways_quiet"
    SIDEWAYS_CHOP = "sideways_chop"
    UNKNOWN = "unknown"


@dataclass
class RegimeAnalysis:
    """Complete regime analysis result."""
    regime: MarketRegime
    trend_strength: float      # ADX value
    volatility_ratio: float    # ATR / MA(ATR, 50)
    ema_200: float
    atr_14: float
    is_bullish: bool
    is_bearish: bool
    confidence: float          # 0-1 confidence score


class RegimeDetector:
    """
    Market Regime Detection System.

    Uses ADX for trend strength and ATR ratio for volatility measurement.
    Classifies market into one of four regimes for adaptive trading.
    """

    # Thresholds
    ADX_THRESHOLD = 25.0        # ADX > 25 = Trending market
    ATR_VOL_THRESHOLD = 1.2     # ATR Ratio > 1.2 = High volatility

    def __init__(
        self,
        window_short: int = 14,
        window_long: int = 50,
        ema_period: int = 200,
    ):
        """
        Initialize regime detector.

        Args:
            window_short: Short window for ATR and ADX calculation (default: 14)
            window_long: Long window for ATR moving average (default: 50)
            ema_period: EMA period for trend direction (default: 200)
        """
        self.window_short = window_short
        self.window_long = window_long
        self.ema_period = ema_period

    def calculate_adx(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Average Directional Index (ADX).

        ADX measures trend strength:
        - ADX > 25: Strong trend
        - ADX < 20: Weak trend / Sideways
        - ADX > 40: Very strong trend

        Returns:
            Series with ADX values
        """
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

        # +DM and -DM
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Smoothed ATR
        atr = pd.Series(tr).ewm(span=self.window_short, adjust=False).mean()

        # +DI and -DI
        plus_di = 100 * pd.Series(plus_dm).ewm(span=self.window_short, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).ewm(span=self.window_short, adjust=False).mean() / atr

        # DX
        di_sum = plus_di + minus_di
        di_diff = abs(plus_di - minus_di)
        dx = 100 * di_diff / (di_sum + 1e-10)  # Avoid division by zero

        # ADX (smoothed DX)
        adx = dx.ewm(span=self.window_short, adjust=False).mean()

        return adx

    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Average True Range (ATR).

        Returns:
            Series with ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(span=self.window_short, adjust=False).mean()
        return atr

    def calculate_atr_ratio(self, df: pd.DataFrame) -> float:
        """
        Calculate ATR ratio (current ATR / MA of ATR).

        Measures relative volatility:
        - Ratio > 1.2: Higher than normal volatility
        - Ratio < 0.8: Lower than normal volatility
        - Ratio ≈ 1.0: Normal volatility

        Returns:
            Current ATR ratio
        """
        atr = self.calculate_atr(df)
        atr_ma = atr.rolling(window=self.window_long).mean()

        current_atr = atr.iloc[-1]
        avg_atr = atr_ma.iloc[-1]

        if avg_atr > 0:
            return current_atr / avg_atr
        return 1.0

    def calculate_ema(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return df['close'].ewm(span=self.ema_period, adjust=False).mean()

    def detect_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime.

        Classification Logic:
        ┌───────────────────────────────────────────────────┐
        │           ATR Ratio (ATR / MA50)                  │
        │                    │                              │
        │         < 1.2      │      >= 1.2                  │
        │    ┌───────────────┼───────────────┐              │
        │ A  │ STABLE_TREND  │ VOLATILE_TREND│  Trend      │
        │ D  │               │               │  (ADX>25)   │
        │ X  ├───────────────┼───────────────┤              │
        │    │ SIDEWAYS_QUIET│ SIDEWAYS_CHOP │  Sideways   │
        │    │               │               │  (ADX≤25)   │
        │    └───────────────┴───────────────┘              │
        └───────────────────────────────────────────────────┘

        Returns:
            MarketRegime classification
        """
        if len(df) < self.window_long:
            return MarketRegime.UNKNOWN

        adx = self.calculate_adx(df)
        current_adx = adx.iloc[-1]
        atr_ratio = self.calculate_atr_ratio(df)

        # 4-Quadrant Classification
        is_trending = current_adx > self.ADX_THRESHOLD
        is_volatile = atr_ratio >= self.ATR_VOL_THRESHOLD

        if is_trending:
            if is_volatile:
                return MarketRegime.VOLATILE_TREND
            else:
                return MarketRegime.STABLE_TREND
        else:
            if is_volatile:
                return MarketRegime.SIDEWAYS_CHOP
            else:
                return MarketRegime.SIDEWAYS_QUIET

    def analyze(self, df: pd.DataFrame) -> RegimeAnalysis:
        """
        Perform complete regime analysis.

        Returns:
            RegimeAnalysis with all metrics and classification
        """
        if len(df) < self.window_long:
            return RegimeAnalysis(
                regime=MarketRegime.UNKNOWN,
                trend_strength=0.0,
                volatility_ratio=1.0,
                ema_200=0.0,
                atr_14=0.0,
                is_bullish=False,
                is_bearish=False,
                confidence=0.0,
            )

        # Calculate indicators
        adx = self.calculate_adx(df)
        current_adx = float(adx.iloc[-1])

        atr = self.calculate_atr(df)
        current_atr = float(atr.iloc[-1])

        atr_ratio = self.calculate_atr_ratio(df)

        ema = self.calculate_ema(df)
        current_ema = float(ema.iloc[-1])

        current_price = float(df['close'].iloc[-1])

        # Determine trend direction
        is_bullish = current_price > current_ema
        is_bearish = current_price < current_ema

        # Detect regime
        regime = self.detect_regime(df)

        # Calculate confidence (based on how far from thresholds)
        adx_distance = abs(current_adx - self.ADX_THRESHOLD) / self.ADX_THRESHOLD
        vol_distance = abs(atr_ratio - self.ATR_VOL_THRESHOLD) / self.ATR_VOL_THRESHOLD
        confidence = min(1.0, (adx_distance + vol_distance) / 2)

        return RegimeAnalysis(
            regime=regime,
            trend_strength=current_adx,
            volatility_ratio=atr_ratio,
            ema_200=current_ema,
            atr_14=current_atr,
            is_bullish=is_bullish,
            is_bearish=is_bearish,
            confidence=confidence,
        )

    def get_regime_description(self, regime: MarketRegime) -> str:
        """Get human-readable description of regime."""
        descriptions = {
            MarketRegime.STABLE_TREND: "Stable Trend - Strong momentum with low volatility. Optimal for grid trading.",
            MarketRegime.VOLATILE_TREND: "Volatile Trend - Strong momentum with high volatility. Trade cautiously.",
            MarketRegime.SIDEWAYS_QUIET: "Sideways Quiet - No trend, low volatility. Good for range trading.",
            MarketRegime.SIDEWAYS_CHOP: "Sideways Chop - No trend, high volatility. Reduce position size.",
            MarketRegime.UNKNOWN: "Unknown - Insufficient data for classification.",
        }
        return descriptions.get(regime, "Unknown regime")


# Example usage
if __name__ == "__main__":
    print("Market Regime Detector V9.5")
    print("=" * 50)
    print("\nRegime Classification:")
    print("  - STABLE_TREND: ADX > 25, ATR Ratio < 1.2")
    print("  - VOLATILE_TREND: ADX > 25, ATR Ratio >= 1.2")
    print("  - SIDEWAYS_QUIET: ADX <= 25, ATR Ratio < 1.2")
    print("  - SIDEWAYS_CHOP: ADX <= 25, ATR Ratio >= 1.2")

    detector = RegimeDetector()
    print(f"\nConfiguration:")
    print(f"  ADX Threshold: {detector.ADX_THRESHOLD}")
    print(f"  ATR Vol Threshold: {detector.ATR_VOL_THRESHOLD}")
    print(f"  Short Window: {detector.window_short}")
    print(f"  Long Window: {detector.window_long}")
    print(f"  EMA Period: {detector.ema_period}")
