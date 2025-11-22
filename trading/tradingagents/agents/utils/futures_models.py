"""
Data models for futures trading.

Standardises structures used across the futures trading agents.
Uses Pydantic for structured, type-safe communication between agents.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime


@dataclass
class FuturesPosition:
    """Futures position snapshot."""
    symbol: str
    position_amt: float  # Position size (positive = long, negative = short)
    entry_price: float  # Average entry price
    mark_price: float  # Current mark price
    unrealized_profit: float  # Unrealized PnL
    liquidation_price: float  # Liquidation price
    leverage: int  # Applied leverage
    margin_type: str  # Margin mode (ISOLATED/CROSSED)
    isolated_margin: float  # Isolated margin amount
    position_side: str = "BOTH"  # Position orientation (BOTH/LONG/SHORT)
    
    @property
    def is_long(self) -> bool:
        """Return True when the position is net long."""
        return self.position_amt > 0

    @property
    def is_short(self) -> bool:
        """Return True when the position is net short."""
        return self.position_amt < 0

    @property
    def pnl_percentage(self) -> float:
        """Unrealized profit and loss percentage."""
        if self.entry_price == 0:
            return 0.0
        return (self.unrealized_profit / (abs(self.position_amt) * self.entry_price)) * 100

    @property
    def liquidation_distance_pct(self) -> float:
        """Percentage distance from the liquidation price."""
        if self.liquidation_price == 0:
            return 100.0
        return abs((self.mark_price - self.liquidation_price) / self.mark_price) * 100


@dataclass
class FuturesAccount:
    """Futures account metrics."""
    total_wallet_balance: float  # Total wallet balance
    total_unrealized_profit: float  # Total unrealized profit
    total_margin_balance: float  # Total margin balance
    total_position_initial_margin: float  # Total position initial margin
    total_open_order_initial_margin: float  # Total open order initial margin
    available_balance: float  # Available balance
    max_withdraw_amount: float  # Maximum withdrawable amount
    
    @property
    def margin_ratio(self) -> float:
        """Maintenance margin ratio."""
        if self.total_margin_balance == 0:
            return 0.0
        # Simplified: (position margin + order margin) / total margin balance
        return (self.total_position_initial_margin + self.total_open_order_initial_margin) / self.total_margin_balance

    @property
    def equity(self) -> float:
        """Account equity."""
        return self.total_wallet_balance + self.total_unrealized_profit


@dataclass
class TradingPlan:
    """Structured trading plan."""
    symbol: str
    direction: str  # "LONG" or "SHORT"
    leverage: int  # Leverage multiplier
    position_size_usd: float  # Position notional in USD
    entry_strategy: str  # Entry strategy description (e.g., "limit_band:70500-71000")
    entry_price_low: Optional[float] = None  # Lower entry price
    entry_price_high: Optional[float] = None  # Upper entry price
    scaling_config: List[Dict] = field(default_factory=list)  # Scaling configuration
    stop_loss_price: float = 0.0  # Stop-loss price
    take_profit_levels: List[Dict] = field(default_factory=list)  # Take-profit configuration
    time_in_force_sec: int = 3600  # Time in force (seconds)
    trigger_type: str = "MARK_PRICE"  # Trigger price type
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "leverage": self.leverage,
            "position_size_usd": self.position_size_usd,
            "entry_strategy": self.entry_strategy,
            "entry_price_low": self.entry_price_low,
            "entry_price_high": self.entry_price_high,
            "scaling_config": self.scaling_config,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_levels": self.take_profit_levels,
            "time_in_force_sec": self.time_in_force_sec,
            "trigger_type": self.trigger_type,
        }


@dataclass
class RiskActionPlan:
    """Risk action playbook."""
    symbol: str
    margin_ratio_threshold: float = 0.70  # Margin ratio threshold
    liquidation_distance_atr_threshold: float = 3.0  # Liquidation distance threshold (ATR multiples)
    unrealized_pnl_pct_threshold: float = -8.0  # Unrealized PnL threshold (%)
    
    # Triggered actions
    reduce_position_pct: float = 25.0  # Reduction percentage
    max_reduce_times: int = 3  # Maximum number of reductions
    cooldown_sec: int = 600  # Cooldown time (seconds)
    flatten_on_extreme: bool = True  # Fully exit in extreme conditions
    
    valid_for_sec: int = 3600  # Plan validity (seconds)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "thresholds": {
                "margin_ratio": self.margin_ratio_threshold,
                "liquidation_distance_atr": self.liquidation_distance_atr_threshold,
                "unrealized_pnl_pct": self.unrealized_pnl_pct_threshold,
            },
            "actions": {
                "reduce_position_pct": self.reduce_position_pct,
                "max_reduce_times": self.max_reduce_times,
                "cooldown_sec": self.cooldown_sec,
                "flatten_on_extreme": self.flatten_on_extreme,
            },
            "valid_for_sec": self.valid_for_sec,
        }


@dataclass
class MarketFeatures:
    """Market features (H1 timeframe)."""
    symbol: str
    current_price: float
    mark_price: float
    
    # Trend indicators
    trend_direction: str  # "UP", "DOWN", "SIDEWAYS"
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    
    # Volatility
    atr_1h: float = 0.0  # 1-hour ATR
    volatility_regime: str = "NORMAL"  # "LOW", "NORMAL", "HIGH"
    
    # Futures-specific metrics
    funding_rate: float = 0.0  # Funding rate
    funding_rate_trend: str = "NEUTRAL"  # "BULLISH", "BEARISH", "NEUTRAL"
    open_interest: float = 0.0  # Open interest
    oi_change_pct: float = 0.0  # Open interest change percentage
    
    # Support/resistance
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "mark_price": self.mark_price,
            "trend": {
                "direction": self.trend_direction,
                "sma_50": self.sma_50,
                "sma_200": self.sma_200,
            },
            "volatility": {
                "atr_1h": self.atr_1h,
                "regime": self.volatility_regime,
            },
            "futures_metrics": {
                "funding_rate": self.funding_rate,
                "funding_rate_trend": self.funding_rate_trend,
                "open_interest": self.open_interest,
                "oi_change_pct": self.oi_change_pct,
            },
            "levels": {
                "support": self.support_level,
                "resistance": self.resistance_level,
            }
        }


@dataclass
class PortfolioRiskMetrics:
    """Portfolio risk metrics."""
    symbol: str
    
    # Account-level
    total_equity: float
    available_balance: float
    margin_ratio: float  # Current margin ratio
    max_leverage_used: int  # Maximum leverage used
    
    # Position-level (when a position exists)
    position_size_usd: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    liquidation_price: float = 0.0
    liquidation_distance_pct: float = 100.0  # Distance to liquidation in percent
    liquidation_distance_atr: float = 0.0  # Distance to liquidation in ATR multiples
    
    # Capacity for new positions
    max_position_size_usd: float = 0.0  # Based on available balance and leverage limits
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "account": {
                "total_equity": self.total_equity,
                "available_balance": self.available_balance,
                "margin_ratio": self.margin_ratio,
                "max_leverage_used": self.max_leverage_used,
            },
            "position": {
                "size_usd": self.position_size_usd,
                "unrealized_pnl": self.unrealized_pnl,
                "unrealized_pnl_pct": self.unrealized_pnl_pct,
                "liquidation_price": self.liquidation_price,
                "liquidation_distance_pct": self.liquidation_distance_pct,
                "liquidation_distance_atr": self.liquidation_distance_atr,
            },
            "capacity": {
                "max_position_size_usd": self.max_position_size_usd,
            }
        }


def calculate_position_size(
    available_balance: float,
    leverage: int,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float
) -> float:
    """
    Calculate a leverage-aware position size under risk constraints.
    
    Args:
        available_balance: Available balance.
        leverage: Leverage multiplier.
        risk_pct: Fraction of equity to risk (e.g., 0.02 for 2%).
        entry_price: Proposed entry price.
        stop_loss_price: Proposed stop-loss price.
        
    Returns:
        Position size in USD.
    """
    # Maximum notional based on margin and leverage
    max_position = available_balance * leverage
    
    # Risk-based position: risk amount divided by per-unit exposure
    risk_amount = available_balance * risk_pct
    price_risk = abs(entry_price - stop_loss_price)
    risk_based_position = risk_amount / (price_risk / entry_price) if price_risk > 0 else 0
    
    # Choose the more conservative (smaller) value
    return min(max_position, risk_based_position)


# ==================== Structured Agent Communication Models ====================
# These models replace string-based reports with type-safe structured data

class TrendAnalysis(BaseModel):
    """Trend analysis for a specific timeframe."""
    direction: str = Field(..., description="Trend direction: UP, DOWN, or SIDEWAYS")
    sma_50: Optional[float] = Field(None, description="50-period SMA")
    sma_200: Optional[float] = Field(None, description="200-period SMA")
    assessment: str = Field(..., description="Brief trend assessment")


class VolatilityAnalysis(BaseModel):
    """Volatility metrics."""
    atr: float = Field(..., description="Average True Range")
    atr_pct: float = Field(..., description="ATR as percentage of price")
    regime: str = Field(..., description="Volatility regime: LOW, NORMAL, or HIGH")


class PriceLevels(BaseModel):
    """Key price levels."""
    current_price: float = Field(..., description="Current market price")
    support: Optional[float] = Field(None, description="Support level")
    resistance: Optional[float] = Field(None, description="Resistance level")
    entry_zone_low: Optional[float] = Field(None, description="Lower entry zone")
    entry_zone_high: Optional[float] = Field(None, description="Upper entry zone")


class FundingAnalysis(BaseModel):
    """Funding rate analysis."""
    rate: float = Field(..., description="Current funding rate")
    trend: str = Field(..., description="Funding trend: BULLISH, BEARISH, or NEUTRAL")
    annualized_pct: float = Field(..., description="Annualized funding rate percentage")


class OpenInterestAnalysis(BaseModel):
    """Open interest analysis."""
    value: float = Field(..., description="Current open interest value")
    bias: str = Field(..., description="OI trend: INCREASING, DECREASING, or STABLE")


class SecondaryTimeframe(BaseModel):
    """Analysis for a secondary timeframe."""
    interval: str = Field(..., description="Timeframe interval (e.g., 5m, 15m, 4h)")
    trend: str = Field(..., description="Trend direction: UP, DOWN, or SIDEWAYS")
    signal: str = Field(..., description="Signal or insight from this timeframe")
    support_resistance_note: str = Field(..., description="Support/resistance observation")


class MarketRecommendation(BaseModel):
    """Market analyst's recommendation."""
    bias: str = Field(..., description="Overall bias: LONG, SHORT, or NEUTRAL")
    stop_loss: Optional[float] = Field(None, description="Suggested stop loss level")
    take_profit: Optional[float] = Field(None, description="Suggested take profit level")
    notes: str = Field(..., description="Additional notes or context")


class MarketAnalysis(BaseModel):
    """Structured market analysis output from MarketAnalyst."""
    symbol: str = Field(..., description="Trading symbol")
    as_of: str = Field(..., description="Analysis timestamp")
    primary_interval: str = Field(..., description="Primary analysis timeframe")
    
    # Primary timeframe analysis
    primary: Dict[str, Any] = Field(..., description="Primary timeframe data")
    
    # Secondary timeframes
    secondary_timeframes: List[SecondaryTimeframe] = Field(default_factory=list, description="Secondary timeframe analyses")
    
    # Futures-specific metrics
    funding: FundingAnalysis = Field(..., description="Funding rate analysis")
    open_interest: OpenInterestAnalysis = Field(..., description="Open interest analysis")
    
    # Recommendation
    recommendation: MarketRecommendation = Field(..., description="Trading recommendation")
    
    # Optional summary text
    summary: Optional[str] = Field(None, description="Brief text summary (1-2 bullet points)")


class PositionInfo(BaseModel):
    """Current position information."""
    side: str = Field(..., description="Position side: LONG or SHORT")
    quantity: float = Field(..., description="Position quantity")
    notional: float = Field(..., description="Position notional value in USD")
    entry_price: float = Field(..., description="Average entry price")
    mark_price: float = Field(..., description="Current mark price")
    unrealized_pnl: float = Field(..., description="Unrealized profit/loss")
    unrealized_pnl_pct: float = Field(..., description="Unrealized PnL percentage")
    liquidation_price: float = Field(..., description="Liquidation price")
    distance_to_liq_pct: float = Field(..., description="Distance to liquidation in percentage")
    distance_to_liq_atr: float = Field(..., description="Distance to liquidation in ATR multiples")
    risk_level: str = Field(..., description="Risk level: SAFE, MODERATE, or DANGEROUS")
    leverage: int = Field(..., description="Applied leverage")
    margin_type: str = Field(..., description="Margin type: CROSSED or ISOLATED")


class AccountInfo(BaseModel):
    """Account balance and margin info."""
    total_equity: float = Field(..., description="Total account equity")
    available_balance: float = Field(..., description="Available balance for trading")
    margin_ratio: float = Field(..., description="Current margin ratio")


class EntryFeasibility(BaseModel):
    """Entry feasibility assessment."""
    can_enter: bool = Field(..., description="Whether entry is feasible")
    suggested_position_usd: float = Field(..., description="Suggested position size in USD")
    suggested_leverage: int = Field(..., description="Suggested leverage")
    margin_required: float = Field(..., description="Margin required for entry")
    risk_budget_usd: float = Field(..., description="Available risk budget in USD")


class PortfolioRecommendation(BaseModel):
    """Portfolio analyst's recommendation."""
    action: str = Field(..., description="Recommended action: HOLD, ADD, REDUCE, EXIT, ENTER, or NONE")
    reason: str = Field(..., description="Reason for recommendation")
    suggested_stop_loss: Optional[float] = Field(None, description="Suggested stop loss price")
    suggested_take_profit: Optional[float] = Field(None, description="Suggested take profit price")


class PortfolioStatus(BaseModel):
    """Structured portfolio status output from PortfolioAnalyst."""
    symbol: str = Field(..., description="Trading symbol")
    account: AccountInfo = Field(..., description="Account information")
    position: Optional[PositionInfo] = Field(None, description="Current position (null if no position)")
    entry_feasibility: EntryFeasibility = Field(..., description="Entry feasibility assessment")
    recommendation: PortfolioRecommendation = Field(..., description="Portfolio recommendation")
    alerts: List[str] = Field(default_factory=list, description="Risk alerts and warnings")
    
    # Optional summary text
    summary: Optional[str] = Field(None, description="Brief text summary (1-2 bullet points)")


class StopLossConfig(BaseModel):
    """Stop loss configuration."""
    price: float = Field(..., description="Stop loss price")
    trigger: str = Field("MARK_PRICE", description="Trigger type")
    distance_atr: Optional[float] = Field(None, description="Distance in ATR multiples")


class TakeProfitLevel(BaseModel):
    """Take profit level configuration."""
    level: int = Field(..., description="Level number (1, 2, 3, etc.)")
    price: float = Field(..., description="Take profit price")
    percent: float = Field(..., description="Percentage of position to close at this level")


class ScalingBatch(BaseModel):
    """Position scaling batch."""
    batch: int = Field(..., description="Batch number")
    percent: float = Field(..., description="Percentage of total position for this batch")
    price: float = Field(..., description="Entry price for this batch")


class RiskAssessment(BaseModel):
    """Risk assessment for the trading plan."""
    risk_level: str = Field(..., description="Overall risk level: LOW, MEDIUM, HIGH, or EXTREME")
    confidence: float = Field(..., description="Confidence level (0-1)")
    max_loss_usd: float = Field(..., description="Maximum potential loss in USD")
    max_loss_pct: float = Field(..., description="Maximum potential loss as percentage")
    risk_reward_ratio: float = Field(..., description="Risk-reward ratio")
    liquidation_risk: str = Field(..., description="Liquidation risk: NONE, LOW, MEDIUM, or HIGH")
    key_risks: List[str] = Field(default_factory=list, description="Key identified risks")


class TradingJustification(BaseModel):
    """Justification for trading decisions."""
    why_this_direction: str = Field(..., description="Rationale for direction (LONG/SHORT/HOLD)")
    why_this_position_size: str = Field(..., description="Rationale for position size")
    why_this_leverage: str = Field(..., description="Rationale for leverage choice")
    why_this_stop_loss: str = Field(..., description="Rationale for stop loss placement")
    risk_vs_reward: str = Field(..., description="Risk-reward analysis")
    alternative_considered: str = Field(..., description="Alternative strategies considered")


class RiskActionThresholds(BaseModel):
    """Risk action thresholds."""
    margin_ratio: float = Field(..., description="Margin ratio threshold")
    liquidation_distance_atr: float = Field(..., description="Liquidation distance threshold (ATR)")
    unrealized_pnl_pct: float = Field(..., description="Unrealized PnL threshold (%)")


class RiskActions(BaseModel):
    """Risk mitigation actions."""
    reduce_position_pct: float = Field(..., description="Position reduction percentage")
    max_reduce_times: int = Field(..., description="Maximum number of reductions")
    cooldown_sec: int = Field(..., description="Cooldown between actions (seconds)")
    flatten_on_extreme: bool = Field(..., description="Whether to fully exit in extreme conditions")


class RiskActionPlanStructured(BaseModel):
    """Risk action plan (structured version)."""
    symbol: str = Field(..., description="Trading symbol")
    thresholds: RiskActionThresholds = Field(..., description="Risk thresholds")
    actions: RiskActions = Field(..., description="Mitigation actions")
    valid_for_sec: int = Field(..., description="Plan validity duration (seconds)")


class TradingPlanStructured(BaseModel):
    """Structured trading plan output from Trader."""
    action: str = Field(..., description="Trading action: LONG, SHORT, or HOLD")
    symbol: str = Field(..., description="Trading symbol")
    position_size_usd: float = Field(..., description="Position size in USD")
    position_size_pct: float = Field(..., description="Position size as percentage of equity")
    leverage: int = Field(..., description="Leverage to use")
    entry_strategy: str = Field(..., description="Entry strategy: MARKET, LIMIT, or LIMIT_BAND")
    entry_price: Optional[float] = Field(None, description="Entry price (null for market orders)")
    scaling: List[ScalingBatch] = Field(default_factory=list, description="Scaling configuration")
    stop_loss: StopLossConfig = Field(..., description="Stop loss configuration")
    take_profit: List[TakeProfitLevel] = Field(default_factory=list, description="Take profit levels")
    time_in_force_sec: int = Field(..., description="Order time in force (seconds)")
    risk_assessment: RiskAssessment = Field(..., description="Risk assessment")
    justification: TradingJustification = Field(..., description="Decision justification")
    risk_action_plan: RiskActionPlanStructured = Field(..., description="Risk action plan")
    
    # Optional summary text
    summary: Optional[str] = Field(None, description="Brief decision summary (1-2 bullet points)")


class ExecutionResult(BaseModel):
    """Structured execution result output from Executor."""
    symbol: str = Field(..., description="Trading symbol")
    action_taken: str = Field(..., description="Action executed: OPENED_LONG, OPENED_SHORT, HELD, REDUCED, CLOSED, FAILED")
    success: bool = Field(..., description="Whether execution was successful")
    
    # Position details (if successful)
    position_size: Optional[float] = Field(None, description="Position size")
    position_size_usd: Optional[float] = Field(None, description="Position size in USD")
    leverage: Optional[int] = Field(None, description="Applied leverage")
    entry_price: Optional[float] = Field(None, description="Entry price")
    stop_loss_price: Optional[float] = Field(None, description="Stop loss price")
    take_profit_price: Optional[float] = Field(None, description="Take profit price")
    
    # Order IDs
    order_ids: Dict[str, str] = Field(default_factory=dict, description="Order IDs (entry, stop_loss, take_profit)")
    
    # Error information (if failed)
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    suggestion: Optional[str] = Field(None, description="Suggestion for adjustment")
    
    # Summary text
    summary: str = Field(..., description="Execution summary text")


