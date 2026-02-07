"""
AYC Fund - ATR Grid Strategy V9.5

Core trading strategy components for Bybit AI Trading Competition 2026.
"""

from .atr_grid_strategy import (
    ATRGridStrategy,
    GridDirection,
    GridLevel,
    GridState,
    MarketRegime,
    RegimeConfig,
    REGIME_CONFIGS,
)

from .regime_detector import (
    RegimeDetector,
    RegimeAnalysis,
)

from .risk_manager import (
    CapitalGuard,
    RiskManager,
    RiskCheckResult,
    RiskLevel,
)

__all__ = [
    # Strategy
    "ATRGridStrategy",
    "GridDirection",
    "GridLevel",
    "GridState",
    "MarketRegime",
    "RegimeConfig",
    "REGIME_CONFIGS",

    # Regime Detection
    "RegimeDetector",
    "RegimeAnalysis",

    # Risk Management
    "CapitalGuard",
    "RiskManager",
    "RiskCheckResult",
    "RiskLevel",
]

__version__ = "9.5"
__author__ = "AYC Fund (YC W22)"
