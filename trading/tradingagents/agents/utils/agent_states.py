from typing import Annotated, Sequence
from datetime import date, timedelta, datetime
from typing_extensions import TypedDict, Optional
from langchain_openai import ChatOpenAI
from tradingagents.agents import *
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, StateGraph, START, MessagesState


# Researcher team state
class InvestDebateState(TypedDict):
    bull_history: Annotated[
        str, "Bullish Conversation history"
    ]  # Bullish Conversation history
    bear_history: Annotated[
        str, "Bearish Conversation history"
    ]  # Bullish Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    current_response: Annotated[str, "Latest response"]  # Last response
    judge_decision: Annotated[str, "Final judge decision"]  # Last response
    count: Annotated[int, "Length of the current conversation"]  # Conversation length


# Risk management team state
class RiskDebateState(TypedDict):
    risky_history: Annotated[
        str, "Risky Agent's Conversation history"
    ]  # Conversation history
    safe_history: Annotated[
        str, "Safe Agent's Conversation history"
    ]  # Conversation history
    neutral_history: Annotated[
        str, "Neutral Agent's Conversation history"
    ]  # Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    latest_speaker: Annotated[str, "Analyst that spoke last"]
    current_risky_response: Annotated[
        str, "Latest response by the risky analyst"
    ]  # Last response
    current_safe_response: Annotated[
        str, "Latest response by the safe analyst"
    ]  # Last response
    current_neutral_response: Annotated[
        str, "Latest response by the neutral analyst"
    ]  # Last response
    judge_decision: Annotated[str, "Judge's decision"]
    count: Annotated[int, "Length of the current conversation"]  # Conversation length


class AgentState(MessagesState):
    """
    Simplified agent state using pure text communication.
    
    Philosophy: LLMs excel at processing text. Structured data adds complexity
    without value when agents only pass text to each other.
    """
    # ==================== CORE METADATA ====================
    trading_symbol: Annotated[str, "Trading symbol (e.g., BTCUSDT) currently being evaluated"]
    trade_date: Annotated[str, "What date we are trading at"]
    sender: Annotated[str, "Agent that sent this message"]
    
    # ==================== RECORDING & TRACKING ====================
    record_id: Annotated[str, "UUID for this trading round (for external recording)"]
    trader_id: Annotated[str, "Trader UUID from config.yaml (e.g., '7bac06d6-3c9c-4af4-87b0-389820be0b37')"]
    order_id: Annotated[Optional[str], "Order ID when a trade is executed"]

    # ==================== AGENT REPORTS (Pure Text) ====================
    # Each agent outputs a focused, structured TEXT report (not JSON)
    
    technical_research_report: Annotated[str, "Technical research report from Research Technical"]
    risk_assessment: Annotated[str, "Risk assessment report from Risk Manager"]
    portfolio_plan: Annotated[str, "Portfolio plan from Portfolio Manager"]
    
    # ==================== HUMAN-FRIENDLY SUMMARIES ====================
    # Plain language explanations of each agent's thinking process
    
    technical_research_summary: Annotated[str, "Plain language summary of technical research thinking"]
    risk_assessment_summary: Annotated[str, "Plain language summary of risk manager thinking"]
    portfolio_plan_summary: Annotated[str, "Plain language summary of portfolio manager thinking"]
    trade_report_summary: Annotated[str, "Plain language summary of trader actions (concise, no technical details)"]
