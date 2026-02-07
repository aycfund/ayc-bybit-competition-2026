"""
Risk Manager - CapitalGuard Implementation

Implements the 50% Rule and other risk management mechanisms.

Author: AYC Fund (YC W22)
Version: 9.5
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level classification."""
    SAFE = "safe"           # < 40% margin usage
    WARNING = "warning"     # 40-50% margin usage
    BLOCKED = "blocked"     # > 50% margin usage
    EMERGENCY = "emergency" # Critical drawdown


@dataclass
class RiskCheckResult:
    """Result of risk check."""
    allowed: bool
    risk_level: RiskLevel
    margin_ratio: float
    message: str
    details: Optional[Dict] = None


class CapitalGuard:
    """
    CapitalGuard - 50% Rule Implementation.

    Prevents over-leveraging by limiting margin usage to 50% of equity.
    This ensures sufficient buffer for drawdowns and margin calls.

    Risk Levels:
    - SAFE (< 40%): Normal trading allowed
    - WARNING (40-50%): Trading allowed with caution
    - BLOCKED (> 50%): New entries blocked
    """

    # Configuration
    MAX_MARGIN_RATIO = 0.50      # 50% maximum margin usage
    WARNING_THRESHOLD = 0.40     # 40% warning level
    EMERGENCY_DRAWDOWN = 0.15    # 15% emergency stop

    def __init__(
        self,
        max_margin_ratio: float = 0.50,
        warning_threshold: float = 0.40,
        emergency_drawdown: float = 0.15,
    ):
        """
        Initialize CapitalGuard.

        Args:
            max_margin_ratio: Maximum allowed margin as % of equity (default: 0.50)
            warning_threshold: Warning level for margin usage (default: 0.40)
            emergency_drawdown: Emergency stop drawdown level (default: 0.15)
        """
        self.max_margin_ratio = max_margin_ratio
        self.warning_threshold = warning_threshold
        self.emergency_drawdown = emergency_drawdown

    def check_entry(
        self,
        equity: float,
        current_margin: float,
        proposed_margin: float,
    ) -> RiskCheckResult:
        """
        Check if a new entry is allowed based on margin limits.

        Args:
            equity: Current account equity
            current_margin: Currently used margin
            proposed_margin: Additional margin for new entry

        Returns:
            RiskCheckResult with decision and details
        """
        if equity <= 0:
            return RiskCheckResult(
                allowed=False,
                risk_level=RiskLevel.EMERGENCY,
                margin_ratio=1.0,
                message="Zero or negative equity",
            )

        # Calculate ratios
        safe_balance = equity * self.max_margin_ratio
        total_margin = current_margin + proposed_margin
        margin_ratio = total_margin / equity

        # Determine risk level and decision
        if margin_ratio > self.max_margin_ratio:
            return RiskCheckResult(
                allowed=False,
                risk_level=RiskLevel.BLOCKED,
                margin_ratio=margin_ratio,
                message=f"Margin limit exceeded: {margin_ratio:.1%} > {self.max_margin_ratio:.0%}",
                details={
                    "equity": equity,
                    "current_margin": current_margin,
                    "proposed_margin": proposed_margin,
                    "total_margin": total_margin,
                    "safe_balance": safe_balance,
                }
            )

        if margin_ratio > self.warning_threshold:
            return RiskCheckResult(
                allowed=True,
                risk_level=RiskLevel.WARNING,
                margin_ratio=margin_ratio,
                message=f"Warning: Margin at {margin_ratio:.1%}",
                details={
                    "equity": equity,
                    "total_margin": total_margin,
                    "remaining": safe_balance - total_margin,
                }
            )

        return RiskCheckResult(
            allowed=True,
            risk_level=RiskLevel.SAFE,
            margin_ratio=margin_ratio,
            message=f"Entry allowed: Margin at {margin_ratio:.1%}",
            details={
                "equity": equity,
                "total_margin": total_margin,
                "remaining": safe_balance - total_margin,
            }
        )

    def check_grid_entry(
        self,
        equity: float,
        margin_per_level: float,
        max_levels: int,
        current_margin: float = 0,
    ) -> RiskCheckResult:
        """
        Check if full grid entry is allowed.

        Args:
            equity: Current account equity
            margin_per_level: Margin required per grid level
            max_levels: Maximum number of grid levels
            current_margin: Currently used margin

        Returns:
            RiskCheckResult with decision and details
        """
        potential_margin = margin_per_level * max_levels
        return self.check_entry(equity, current_margin, potential_margin)

    def check_emergency_stop(
        self,
        current_equity: float,
        peak_equity: float,
    ) -> RiskCheckResult:
        """
        Check if emergency stop should be triggered.

        Args:
            current_equity: Current account equity
            peak_equity: Peak equity (high water mark)

        Returns:
            RiskCheckResult indicating if emergency stop needed
        """
        if peak_equity <= 0:
            return RiskCheckResult(
                allowed=True,
                risk_level=RiskLevel.SAFE,
                margin_ratio=0,
                message="No peak equity recorded",
            )

        drawdown = (peak_equity - current_equity) / peak_equity

        if drawdown >= self.emergency_drawdown:
            return RiskCheckResult(
                allowed=False,
                risk_level=RiskLevel.EMERGENCY,
                margin_ratio=drawdown,
                message=f"EMERGENCY STOP: Drawdown {drawdown:.1%} >= {self.emergency_drawdown:.0%}",
                details={
                    "current_equity": current_equity,
                    "peak_equity": peak_equity,
                    "drawdown": drawdown,
                    "threshold": self.emergency_drawdown,
                }
            )

        return RiskCheckResult(
            allowed=True,
            risk_level=RiskLevel.SAFE if drawdown < 0.10 else RiskLevel.WARNING,
            margin_ratio=drawdown,
            message=f"Drawdown: {drawdown:.1%}",
            details={
                "current_equity": current_equity,
                "peak_equity": peak_equity,
                "drawdown": drawdown,
            }
        )

    def calculate_position_size(
        self,
        equity: float,
        capital_pct: float,
        leverage: int,
        current_price: float,
        current_margin: float = 0,
    ) -> Dict:
        """
        Calculate safe position size considering CapitalGuard limits.

        Args:
            equity: Current account equity
            capital_pct: Percentage of equity to use
            leverage: Trading leverage
            current_price: Current asset price
            current_margin: Currently used margin

        Returns:
            Dict with position sizing information
        """
        # Calculate desired position
        desired_value = equity * capital_pct
        desired_margin = desired_value / leverage

        # Check against limits
        safe_balance = equity * self.max_margin_ratio
        available_margin = max(0, safe_balance - current_margin)

        # Adjust if needed
        if desired_margin > available_margin:
            actual_margin = available_margin
            actual_value = actual_margin * leverage
            adjusted = True
        else:
            actual_margin = desired_margin
            actual_value = desired_value
            adjusted = False

        # Calculate quantity
        quantity = actual_value / current_price if current_price > 0 else 0

        return {
            "desired_value": desired_value,
            "desired_margin": desired_margin,
            "actual_value": actual_value,
            "actual_margin": actual_margin,
            "quantity": quantity,
            "adjusted": adjusted,
            "margin_ratio": (current_margin + actual_margin) / equity if equity > 0 else 0,
            "remaining_margin": available_margin - actual_margin,
        }


class RiskManager:
    """
    Complete Risk Management System.

    Combines CapitalGuard with additional risk controls:
    - Position sizing
    - Drawdown monitoring
    - Daily loss limits
    - Correlation limits
    """

    def __init__(
        self,
        max_margin_ratio: float = 0.50,
        emergency_drawdown: float = 0.15,
        daily_loss_limit: float = 0.05,
    ):
        """
        Initialize Risk Manager.

        Args:
            max_margin_ratio: Maximum margin usage (default: 0.50)
            emergency_drawdown: Emergency stop level (default: 0.15)
            daily_loss_limit: Maximum daily loss (default: 0.05)
        """
        self.capital_guard = CapitalGuard(
            max_margin_ratio=max_margin_ratio,
            emergency_drawdown=emergency_drawdown,
        )
        self.daily_loss_limit = daily_loss_limit
        self.peak_equity = 0.0
        self.daily_starting_equity = 0.0

    def update_peak_equity(self, current_equity: float):
        """Update peak equity (high water mark)."""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

    def reset_daily_stats(self, current_equity: float):
        """Reset daily statistics (call at start of day)."""
        self.daily_starting_equity = current_equity

    def check_all_limits(
        self,
        current_equity: float,
        current_margin: float,
        proposed_margin: float,
    ) -> RiskCheckResult:
        """
        Check all risk limits before allowing new entry.

        Args:
            current_equity: Current account equity
            current_margin: Currently used margin
            proposed_margin: Proposed additional margin

        Returns:
            RiskCheckResult with comprehensive risk check
        """
        # 1. Check emergency stop
        self.update_peak_equity(current_equity)
        emergency_check = self.capital_guard.check_emergency_stop(
            current_equity, self.peak_equity
        )
        if not emergency_check.allowed:
            return emergency_check

        # 2. Check daily loss limit
        if self.daily_starting_equity > 0:
            daily_pnl = (current_equity - self.daily_starting_equity) / self.daily_starting_equity
            if daily_pnl <= -self.daily_loss_limit:
                return RiskCheckResult(
                    allowed=False,
                    risk_level=RiskLevel.BLOCKED,
                    margin_ratio=abs(daily_pnl),
                    message=f"Daily loss limit reached: {daily_pnl:.1%}",
                )

        # 3. Check margin limits
        return self.capital_guard.check_entry(
            current_equity, current_margin, proposed_margin
        )


# Example usage
if __name__ == "__main__":
    print("Risk Manager - CapitalGuard V9.5")
    print("=" * 50)

    guard = CapitalGuard()

    # Example scenario
    equity = 10000
    current_margin = 2000
    proposed_margin = 3000

    result = guard.check_entry(equity, current_margin, proposed_margin)

    print(f"\nExample Check:")
    print(f"  Equity: ${equity:,.2f}")
    print(f"  Current Margin: ${current_margin:,.2f}")
    print(f"  Proposed Margin: ${proposed_margin:,.2f}")
    print(f"  Total Margin: ${current_margin + proposed_margin:,.2f}")
    print(f"  Safe Balance (50%): ${equity * 0.5:,.2f}")
    print(f"\nResult:")
    print(f"  Allowed: {result.allowed}")
    print(f"  Risk Level: {result.risk_level.value}")
    print(f"  Margin Ratio: {result.margin_ratio:.1%}")
    print(f"  Message: {result.message}")
