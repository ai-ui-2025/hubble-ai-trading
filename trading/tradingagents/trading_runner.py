"""
Core trading strategy execution module.

Provides the main trading loop and graph construction for the AI trading system.
Uses LangGraph's init_chat_model for unified multi-provider LLM support.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from loguru import logger

from tradingagents.config import (
    AccountConfig,
    ExchangeConfig,
    LLMConfig,
    get_api_key_for_model,
    get_system_config,
    get_research_agent_config,
)
from tradingagents.agents.risk_manager.futures_risk_manager import create_risk_manager
from tradingagents.agents.portfolio_manager.futures_portfolio_manager import create_portfolio_manager
from tradingagents.agents.trader.futures_trader import create_trader
from tradingagents.agents.utils.agent_states import AgentState

from tradingagents.agents.utils.futures_market_tools import (
    initialize_futures_client as initialize_market_client,
    get_futures_market_data,
    get_futures_technical_features,
    get_funding_rate_analysis,
    get_open_interest_analysis,
    get_comprehensive_market_analysis,
    get_exchange_trading_rules,
)
from tradingagents.agents.utils.futures_execution_tools import (
    initialize_futures_client as initialize_execution_client,
    get_comprehensive_trading_status,
    prepare_trading_environment,
    set_futures_leverage,
    set_margin_mode,
    open_long_position,
    open_short_position,
    close_position,
    update_sl_tp,
    update_sl_tp_safe,
    reduce_position,
    cancel_order,
    cancel_all_orders_for_symbol,
)
from tradingagents.agents.utils.agent0_tools_a2a import (
    initialize_agent0_sdk,
    discover_research_agents,
    invoke_research_agent,
)


def initialize_llm(llm_config: LLMConfig) -> BaseChatModel:
    """
    Initialize LLM with automatic provider detection.
    
    Supports OpenAI, DeepSeek (via OpenAI API), Gemini, and Anthropic models.
    Automatically selects the correct provider based on model name.
    
    Args:
        llm_config: LLM configuration object
    
    Returns:
        BaseChatModel instance (ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI, etc.)
    """
    # Get the API key for this model
    api_key = get_api_key_for_model(llm_config.model)
    provider = llm_config.provider
    
    # Initialize the appropriate chat model based on provider
    if provider == "openai":
        llm = ChatOpenAI(
            model=llm_config.model,
            api_key=api_key,
        )
    elif provider == "deepseek":
        # DeepSeek uses OpenAI-compatible API
        llm = ChatOpenAI(
            model=llm_config.model,
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
    elif provider == "gemini":
        # Google Gemini
        llm = ChatGoogleGenerativeAI(
            model=llm_config.model,
            google_api_key=api_key,
        )
    elif provider == "anthropic":
        # Anthropic Claude
        llm = ChatAnthropic(
            model=llm_config.model,
            anthropic_api_key=api_key,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    logger.info(f"✅ Initialized {provider.upper()} model: {llm_config.model}")
    return llm


def create_futures_trading_graph(llm, symbol: str, trade_date: str, checkpointer=None):
    """
    Build the futures trading graph.

    Workflow:
    Risk Manager → Portfolio Manager → Trader → END

    Note: Research agents are invoked dynamically via agent0 a2a protocol
    by the Risk Manager using the invoke_research_agent tool.

    Args:
        llm: Language model instance
        symbol: Trading symbol
        trade_date: Trading date
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled LangGraph workflow
    """
    # Create agent nodes
    risk_manager = create_risk_manager(llm)
    portfolio_manager = create_portfolio_manager(llm)
    trader = create_trader(llm)
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Shared tool executor node
    common_tools = [
        # Agent0 A2A tools - for dynamic research agent invocation
        discover_research_agents,  # Discover research agents via ERC-8004
        invoke_research_agent,  # Invoke research agent via HTTP endpoint
        # Market/analysis tools - comprehensive tool includes orderbook analysis
        get_comprehensive_market_analysis,
        # Legacy tools (kept for granular control if needed)
        get_futures_market_data,
        get_futures_technical_features,
        get_funding_rate_analysis,
        get_open_interest_analysis,
        get_exchange_trading_rules,  # Exchange trading rules (cached)
        # Trading/execution tools
        get_comprehensive_trading_status,  # Comprehensive tool for account + position + orders
        prepare_trading_environment,  # One-stop pre-trade preparation (safety checks + cleanup)
        set_futures_leverage,
        set_margin_mode,
        open_long_position,
        open_short_position,
        close_position,
        update_sl_tp_safe,  # Safe version with built-in safety checks (preferred)
        reduce_position,
        cancel_order,
        cancel_all_orders_for_symbol,
    ]

    risk_manager_tools_node = ToolNode(common_tools)
    trader_tools_node = ToolNode(common_tools)

    # Register nodes
    workflow.add_node("risk_manager", risk_manager)
    workflow.add_node("portfolio_manager", portfolio_manager)
    workflow.add_node("trader", trader)
    workflow.add_node("risk_manager_tools", risk_manager_tools_node)
    workflow.add_node("trader_tools", trader_tools_node)
    
    # Define workflow
    # Start directly from Risk Manager (research agent called via tool)
    workflow.set_entry_point("risk_manager")

    # Risk Manager → Portfolio Manager (with tool support)
    workflow.add_conditional_edges(
        "risk_manager",
        lambda x: "risk_manager_tools" if (x.get("messages") and len(x["messages"]) > 0 and x["messages"][-1].tool_calls) else "portfolio_manager",
        {
            "risk_manager_tools": "risk_manager_tools",
            "portfolio_manager": "portfolio_manager"
        }
    )

    # Tool node returns control to Risk Manager
    workflow.add_edge("risk_manager_tools", "risk_manager")
    
    # Portfolio Manager → Trader
    workflow.add_edge("portfolio_manager", "trader")
    
    # Trader may call tools
    # Philosophy: Trader prompt provides clear step-by-step guidance.
    # LLM follows steps → calls needed tools → generates report → stops.
    # No artificial iteration limits needed - proper prompt prevents infinite loops.
    workflow.add_conditional_edges(
        "trader",
        lambda x: "trader_tools" if (x.get("messages") and len(x["messages"]) > 0 and x["messages"][-1].tool_calls) else END,
        {
            "trader_tools": "trader_tools",
            END: END,
        }
    )
    
    # Tool node returns control to Trader
    workflow.add_edge("trader_tools", "trader")
    
    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    
    return workflow.compile()


def run_trading_strategy(symbol: str, config: Optional[AccountConfig] = None):
    """
    Execute the live trading strategy.
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT"
        config: Account configuration (optional, will use env vars if None)
        
    Returns:
        Final state dict or None if execution failed
    """
    logger.info("="*80)
    logger.info("🚀 AI Futures Trading System")
    logger.info("="*80)
    logger.info(f"Trading pair: {symbol}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.warning("Mode: 💰 Live trading (real funds)")
    logger.info("="*80)
    
    # If config is provided, use it; otherwise fall back to environment variables
    if config is None:
        # Legacy mode: create config from environment variables
        logger.info("Using environment variables for configuration")
        
        api_key = os.getenv("ASTER_API_KEY")
        api_secret = os.getenv("ASTER_API_SECRET")
        
        if not api_key or not api_secret:
            logger.error("❌ Missing ASTER_API_KEY or ASTER_API_SECRET environment variable")
            logger.error("Set the API keys in config.yaml before running.")
            return None
        
        llm_model = os.getenv("LLM_MODEL", "deepseek-chat")
        
        # Validate API key is available
        try:
            get_api_key_for_model(llm_model)
        except ValueError as e:
            logger.error(f"❌ {e}")
            return None
        
        config = AccountConfig(
            name="default",
            symbol=symbol,
            exchange=ExchangeConfig(
                api_key=api_key,
                api_secret=api_secret,
                base_url=os.getenv("ASTER_BASE_URL", "https://fapi.asterdex.com")
            ),
            llm=LLMConfig(
                model=llm_model,
            )
        )
    
    # Initialize exchange client with explicit config (both market and execution tools)
    initialize_market_client(
        api_key=config.exchange.api_key,
        api_secret=config.exchange.api_secret,
        base_url=config.exchange.base_url
    )
    initialize_execution_client(
        api_key=config.exchange.api_key,
        api_secret=config.exchange.api_secret,
        base_url=config.exchange.base_url
    )
    logger.info(f"Exchange API initialized: {config.exchange.base_url}")

    # Initialize agent0 SDK
    from tradingagents.config import get_agent0_config
    agent0_config = get_agent0_config()
    initialize_agent0_sdk(
        chain_id=agent0_config.get("chain_id", 11155111),
        rpc_url=agent0_config.get("rpc_url"),
    )

    # Initialize LLM with explicit config
    llm = initialize_llm(config.llm)
    
    # Build the trading graph with persistent checkpoints
    state_dir = Path("state")
    state_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = state_dir / "trading_memory.sqlite"
    
    logger.info(f"Using checkpoint database: {checkpoint_path}")
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Checkpointer disabled - rely on stateless agent communication
    checkpointer = None
    
    graph = create_futures_trading_graph(llm, symbol, current_date, checkpointer)
    
    # Generate UUID for this trading round
    record_id = str(uuid.uuid4())
    logger.info(f"📝 Trading round ID: {record_id}")
    
    # Log test mode if configured
    if config.test_mode:
        logger.warning(f"🧪 TEST MODE ACTIVE: {config.test_mode.decision} / {config.test_mode.order_type}")
    
    # Initial state for the graph
    initial_state = {
        "messages": [{"role": "user", "content": f"Analyze {symbol} futures market and make trading decision. Account is currently configured in Multi-Assets (cross margin only) mode; avoid assuming isolated margin is available."}],
        "trading_symbol": symbol,
        "trade_date": current_date,
        "record_id": record_id,
        "trader_id": config.trader_id,  # Use trader_id from config.yaml
        "order_id": None,

        # Agent reports (pure text)
        "technical_research_report": "",  # From Research Agent (via a2a)
        "risk_assessment": "",  # From Risk Manager
        "portfolio_plan": "",  # From Portfolio Manager

        # Human-friendly summaries (plain language explanations from each agent)
        "technical_research_summary": "",  # Plain language from Research Agent
        "risk_assessment_summary": "",  # Plain language from Risk Manager
        "portfolio_plan_summary": "",  # Plain language from Portfolio Manager
        "trade_report_summary": "",  # Plain language summary from Trader (concise output)

        # Test mode (if configured)
        "test_mode": config.test_mode,  # Optional: force specific decisions for testing

        # Configuration
        "market_timeframes": {
            "primary": "5m",
            "secondary": ["15m", "1h", "4h"],
        },
    }
    
    logger.info("📊 Starting market analysis...")
    
    def extract_content_text(message) -> str:
        """Convert LangChain message content into a safe string for logging."""
        content = ""
        if message is None:
            return content
        
        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = getattr(message, "content", "")
        
        if isinstance(content, str):
            return content.strip()
        
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return "\n".join(part for part in parts if part).strip()
        
        return str(content).strip()
    
    def extract_tool_calls(message):
        """Extract tool call information from a message."""
        if message is None:
            return []
        
        if isinstance(message, dict):
            tool_calls = message.get("tool_calls") or message.get("additional_kwargs", {}).get("tool_calls")
        else:
            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls is None:
                additional = getattr(message, "additional_kwargs", {}) or {}
                tool_calls = additional.get("tool_calls")
        
        if not tool_calls:
            return []
        
        # Normalize to dict form
        normalized = []
        for call in tool_calls:
            if isinstance(call, dict):
                normalized.append(call)
            else:
                normalized.append(
                    {
                        "name": getattr(call, "name", ""),
                        "args": getattr(call, "args", {}),
                    }
                )
        return normalized
    
    # Execute the graph (stream updates for real-time logging)
    try:
        final_state = {**initial_state}
        last_node = None
        
        stream_config = {
            "recursion_limit": 150,  # Increased from 100 to allow complex operations
            "configurable": {
                "thread_id": config.name,
            },
        }
        stream_kwargs = {"config": stream_config}
        try:
            stream_iterator = graph.stream(initial_state, stream_mode="updates", **stream_kwargs)
        except TypeError:
            stream_iterator = graph.stream(initial_state, **stream_kwargs)
        
        for chunk in stream_iterator:
            if not isinstance(chunk, dict):
                continue
            
            for node_name, node_update in chunk.items():
                if not isinstance(node_update, dict):
                    continue
                
                # Merge incremental state for this node
                final_state.update(node_update)
                
                # Progress hint for node transitions
                if node_name != last_node:
                    logger.info(f"🔄 Node in progress: {node_name}")
                    last_node = node_name
                
                # Log tool call requests from agent nodes (before they go to tool nodes)
                if node_name in {"risk_manager", "trader"}:
                    messages = node_update.get("messages") or []

                    # Check the last message for tool calls
                    if messages:
                        last_message = messages[-1]
                        tool_calls = extract_tool_calls(last_message)

                        if tool_calls:
                            # Map node name to agent name
                            agent_name_map = {
                                "risk_manager": "Risk Manager",
                                "trader": "Trader"
                            }
                            agent_name = agent_name_map.get(node_name, node_name)
                            
                            # Log each tool call
                            for call in tool_calls:
                                tool_name = call.get("name", "unknown_tool")
                                args = call.get("args", {})
                                
                                # Format arguments for display (show all args completely, no truncation)
                                args_str = ", ".join(
                                    f"{k}={v}" for k, v in args.items()
                                )
                                
                                logger.info(f"🔧 [{agent_name}] Calling tool: {tool_name}({args_str})")
                
                # Log tool execution errors from tool nodes
                if node_name in {"risk_manager_tools", "trader_tools"}:
                    messages = node_update.get("messages") or []

                    for message in messages:
                            response_text = extract_content_text(message)
                            if response_text:
                                # Check for actual errors (not just JSON keys containing "error")
                                # Parse as JSON first to detect real errors
                                import json
                                is_error = False
                                try:
                                    data = json.loads(response_text)
                                    # Check if it's an error response (has "error" key with non-empty value)
                                    if isinstance(data, dict) and "error" in data and data["error"]:
                                        is_error = True
                                except (json.JSONDecodeError, TypeError):
                                    # Not JSON, check for text-based error indicators
                                    if "not a valid tool" in response_text.lower():
                                        is_error = True

                                if is_error:
                                    logger.error(f"⚠️  Tool error: {response_text}")

                    # Don't print other info for tool nodes, just continue
                    continue

                # Log text report outputs from each node
                # Note: Research reports are now included in Risk Manager's tool responses
                
                if node_update.get("risk_assessment"):
                    logger.info("\n" + "="*80)
                    logger.info("🛡️ Risk Manager – Assessment Completed")
                    logger.info("="*80)
                    logger.info(node_update["risk_assessment"])
                    
                    # Log human-friendly summary if available
                    if node_update.get("risk_assessment_summary"):
                        logger.info("\n" + "-"*80)
                        logger.info("💭 Plain Language Summary:")
                        logger.info("-"*80)
                        logger.info(node_update["risk_assessment_summary"])
                
                if node_update.get("portfolio_plan"):
                    logger.info("\n" + "="*80)
                    logger.info("💼 Portfolio Manager – Plan Completed")
                    logger.info("="*80)
                    logger.info(node_update["portfolio_plan"])
                    
                    # Log human-friendly summary if available
                    if node_update.get("portfolio_plan_summary"):
                        logger.info("\n" + "-"*80)
                        logger.info("💭 Plain Language Summary:")
                        logger.info("-"*80)
                        logger.info(node_update["portfolio_plan_summary"])
                
                if node_update.get("trade_report_summary"):
                    logger.info("\n" + "="*80)
                    logger.info("✅ Trader – Trade Execution Summary")
                    logger.info("="*80)
                    logger.info(node_update["trade_report_summary"])
        
        logger.info("\n" + "="*80)
        logger.info("✨ Strategy execution completed")
        logger.info("="*80)
        
        # Print final summaries
        return final_state
    
    except Exception as e:
        logger.error(f"\n❌ Execution error: {e}")
        import traceback
        traceback.print_exc()
        return None
