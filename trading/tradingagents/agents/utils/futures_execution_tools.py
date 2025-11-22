"""
Utility functions for futures trade execution.

Provides helper tools that agents can call during execution.
"""

from langchain_core.tools import tool
from typing import Optional, List, Dict
import uuid
import json
import math
from loguru import logger
from requests.exceptions import HTTPError
from tradingagents.dataflows.asterdex_futures_api import AsterFuturesClient
from tradingagents.agents.utils.futures_models import (
    FuturesPosition,
    FuturesAccount,
    TradingPlan,
    calculate_position_size
)


# Global client instance - will be set during initialization
_client: Optional[AsterFuturesClient] = None


def initialize_futures_client(api_key: str, api_secret: str, base_url: str = "https://fapi.asterdex.com") -> None:
    """
    Initialize the futures client with explicit configuration.
    
    Args:
        api_key: Exchange API key
        api_secret: Exchange API secret
        base_url: Exchange API base URL
    """
    global _client
    _client = AsterFuturesClient(api_key=api_key, api_secret=api_secret, base_url=base_url)


def get_futures_client() -> AsterFuturesClient:
    """
    Return the futures client instance.
    
    Raises:
        RuntimeError: If client hasn't been initialized
    """
    global _client
    if _client is None:
        raise RuntimeError(
            "Futures client not initialized. "
            "Call initialize_futures_client() before using execution tools."
        )
    return _client


@tool
def get_futures_account_info(symbol: str = None) -> str:
    """
    Fetch futures account information.
    
    Args:
        symbol: Optional trading pair to include its position snapshot.
        
    Returns:
        JSON string containing account details.
    """
    try:
        client = get_futures_client()
        account_data = client.get_account()
        
        result = {
            "account": {
                "total_equity": account_data["total_wallet_balance"] + account_data["total_unrealized_profit"],
                "available_balance": account_data["available_balance"],
                "total_margin_balance": account_data["total_margin_balance"],
                "total_unrealized_profit": account_data["total_unrealized_profit"],
                "margin_ratio": (account_data["total_position_initial_margin"] + account_data["total_open_order_initial_margin"]) / account_data["total_margin_balance"] if account_data["total_margin_balance"] > 0 else 0,
            }
        }
        
        # Include position details when a symbol is provided
        if symbol:
            positions = client.get_positions(symbol)
            if positions:
                pos = positions[0]
                result["position"] = {
                    "symbol": pos["symbol"],
                    "position_amt": pos["position_amt"],
                    "entry_price": pos["entry_price"],
                    "mark_price": pos["mark_price"],
                    "unrealized_profit": pos["unrealized_profit"],
                    "liquidation_price": pos["liquidation_price"],
                    "leverage": pos["leverage"],
                    "margin_type": pos["margin_type"],
                }
            else:
                result["position"] = {"message": f"No position for {symbol}"}
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_futures_position(symbol: str) -> str:
    """
    Fetch the open position for a specific trading pair.
    
    This tool checks if there's an existing position to prevent duplicate orders.
    When position_amt is 0, it means there's no active position.
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT".
        
    Returns:
        JSON string with position details or "no position" message.
    """
    try:
        client = get_futures_client()
        positions = client.get_positions(symbol)
        
        # Check if position exists with non-zero amount
        if not positions:
            return json.dumps({
                "symbol": symbol,
                "position_exists": False,
                "message": f"No position for {symbol}"
            })
        
        pos = positions[0]
        
        result = {
            "symbol": pos["symbol"],
            "position_exists": True,
            "position_amt": pos["position_amt"],
            "side": "LONG" if pos["position_amt"] > 0 else "SHORT",
            "entry_price": pos["entry_price"],
            "mark_price": pos["mark_price"],
            "unrealized_profit": pos["unrealized_profit"],
            "unrealized_pnl_pct": (pos["unrealized_profit"] / (abs(pos["position_amt"]) * pos["entry_price"])) * 100 if pos["entry_price"] > 0 else 0,
            "liquidation_price": pos["liquidation_price"],
            "liquidation_distance_pct": abs((pos["mark_price"] - pos["liquidation_price"]) / pos["mark_price"]) * 100 if pos["mark_price"] > 0 else 0,
            "leverage": pos["leverage"],
            "margin_type": pos["margin_type"],
            "isolated_margin": pos["isolated_margin"],
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_open_orders(symbol: str) -> str:
    """
    Fetch all open (unfilled) orders for a specific trading pair.
    
    This tool is essential for preventing duplicate orders and understanding margin allocation.
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT".
        
    Returns:
        JSON string with list of open orders and their details.
    """
    try:
        client = get_futures_client()
        open_orders = client.get_open_orders(symbol)
        
        if not open_orders:
            return json.dumps({
                "message": f"No open orders for {symbol}",
                "open_orders": []
            })
        
        # Process and format open orders for easier understanding
        formatted_orders = []
        for order in open_orders:
            formatted_orders.append({
                "order_id": order.get("orderId"),
                "symbol": order.get("symbol"),
                "side": order.get("side"),  # BUY or SELL
                "type": order.get("type"),  # LIMIT, MARKET, STOP, etc.
                "price": float(order.get("price", 0)),
                "quantity": float(order.get("origQty", 0)),
                "filled_quantity": float(order.get("executedQty", 0)),
                "status": order.get("status"),
                "time": order.get("time"),
                "reduce_only": order.get("reduceOnly", False),
                "position_side": order.get("positionSide", "BOTH"),
            })
        
        result = {
            "symbol": symbol,
            "open_orders_count": len(open_orders),
            "open_orders": formatted_orders,
            "warning": "These orders occupy margin. Consider canceling before placing new orders to avoid double-positioning."
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_comprehensive_trading_status(symbol: str) -> str:
    """
    Get comprehensive trading status including account health, position details, and open orders in a single call.
    
    This tool consolidates multiple queries to improve efficiency and reduce API calls.
    Use this tool at the beginning of trade execution to understand the complete trading state.
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT"
        
    Returns:
        JSON string with comprehensive trading status including:
        - Account health (equity, available balance, margin usage)
        - Current position details (if exists)
        - Open orders list
        - Trading capacity assessment
    """
    try:
        client = get_futures_client()
        
        # 1. Fetch account information
        account_data = client.get_account()
        total_equity = account_data["total_wallet_balance"] + account_data["total_unrealized_profit"]
        available_balance = account_data["available_balance"]
        total_margin_balance = account_data["total_margin_balance"]
        margin_used = account_data["total_position_initial_margin"] + account_data["total_open_order_initial_margin"]
        margin_ratio = (margin_used / total_margin_balance * 100) if total_margin_balance > 0 else 0
        
        # Determine margin status
        if margin_ratio > 80:
            margin_status = "CRITICAL"
        elif margin_ratio > 60:
            margin_status = "WARNING"
        else:
            margin_status = "HEALTHY"
        
        # 2. Fetch position information
        position_info = {"position_exists": False}
        try:
            positions = client.get_positions(symbol)
            if positions and abs(float(positions[0].get("position_amt", 0))) > 0:
                pos = positions[0]
                position_amt = float(pos["position_amt"])
                entry_price = float(pos["entry_price"])
                mark_price = float(pos["mark_price"])
                liquidation_price = float(pos["liquidation_price"])
                
                # Calculate distance to liquidation
                distance_to_liq = 0
                if liquidation_price > 0:
                    if position_amt > 0:  # LONG
                        distance_to_liq = ((mark_price - liquidation_price) / mark_price) * 100
                    else:  # SHORT
                        distance_to_liq = ((liquidation_price - mark_price) / mark_price) * 100
                
                # Assess risk level
                if distance_to_liq < 5:
                    risk_level = "CRITICAL"
                elif distance_to_liq < 10:
                    risk_level = "HIGH"
                elif distance_to_liq < 20:
                    risk_level = "MEDIUM"
                else:
                    risk_level = "LOW"
                
                position_info = {
                    "position_exists": True,
                    "side": "LONG" if position_amt > 0 else "SHORT",
                    "position_amt": abs(position_amt),
                    "entry_price": entry_price,
                    "mark_price": mark_price,
                    "unrealized_profit": float(pos["unrealized_profit"]),
                    "liquidation_price": liquidation_price,
                    "distance_to_liquidation_pct": round(distance_to_liq, 2),
                    "leverage": int(pos["leverage"]),
                    "margin_type": pos["margin_type"],
                    "risk_level": risk_level,
                }
        except Exception:
            position_info = {"position_exists": False, "message": f"No position for {symbol}"}
        
        # 3. Fetch open orders
        open_orders_info = {"open_orders_count": 0, "open_orders": []}
        try:
            open_orders = client.get_open_orders(symbol)
            if open_orders:
                formatted_orders = []
                for order in open_orders:
                    formatted_orders.append({
                        "order_id": order.get("orderId"),
                        "side": order.get("side"),
                        "type": order.get("type"),
                        "price": float(order.get("price", 0)),
                        "quantity": float(order.get("origQty", 0)),
                        "filled_quantity": float(order.get("executedQty", 0)),
                        "status": order.get("status"),
                        "reduce_only": order.get("reduceOnly", False),
                        "position_side": order.get("positionSide", "BOTH"),
                    })
                
                open_orders_info = {
                    "open_orders_count": len(open_orders),
                    "open_orders": formatted_orders,
                }
        except Exception:
            open_orders_info = {"open_orders_count": 0, "open_orders": []}
        
        # 4. Consolidate results
        result = {
            "symbol": symbol,
            "account": {
                "total_equity": round(total_equity, 2),
                "available_balance": round(available_balance, 2),
                "margin_used": round(margin_used, 2),
                "margin_ratio_pct": round(margin_ratio, 2),
                "margin_status": margin_status,
            },
            "position": position_info,
            "orders": open_orders_info,
            "timestamp": account_data.get("updateTime"),
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def set_futures_leverage(symbol: str, leverage: int) -> str:
    """
    Set leverage for a futures symbol.
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT".
        leverage: Leverage (1-125).
        
    Returns:
        JSON string describing the result.
    """
    try:
        if leverage < 1 or leverage > 125:
            return json.dumps({"error": "Leverage must be between 1 and 125"})
        
        client = get_futures_client()
        result = client.set_leverage(symbol, leverage)
        
        return json.dumps({
            "success": True,
            "symbol": symbol,
            "leverage": leverage,
            "message": f"Successfully set leverage to {leverage}x for {symbol}"
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def set_margin_mode(symbol: str, margin_type: str = "ISOLATED") -> str:
    """
    Configure margin mode for a symbol.
    
    Args:
        symbol: Trading pair.
        margin_type: "ISOLATED" or "CROSSED".
        
    Returns:
        JSON string describing the result.
    """
    try:
        if margin_type not in ["ISOLATED", "CROSSED"]:
            return json.dumps({"error": "margin_type must be 'ISOLATED' or 'CROSSED'"})
        
        client = get_futures_client()
        result = client.set_margin_type(symbol, margin_type)
        
        return json.dumps({
            "success": True,
            "symbol": symbol,
            "margin_type": margin_type,
            "message": f"Successfully set margin mode to {margin_type} for {symbol}"
        })
        
    except HTTPError as http_err:
        # Aster/Binance returns -4168 when Multi-Assets mode blocks isolated margin
        response = getattr(http_err, "response", None)
        error_payload: Dict = {}
        if response is not None:
            try:
                error_payload = response.json()
            except Exception:
                error_payload = {}
        error_code = error_payload.get("code")
        error_msg = error_payload.get("msg") or str(http_err)
        
        if error_code == -4168:
            return json.dumps({
                "success": True,
                "symbol": symbol,
                "requested_margin_type": margin_type,
                "margin_type": "CROSSED",
                "error_code": error_code,
                "message": (
                    "Account is running in Multi-Assets mode and does not support isolated margin. "
                    "Continuing in CROSSED margin without changing the setting."
                )
            })
        
        return json.dumps({
            "error": str(http_err),
            "details": error_msg,
            "status_code": response.status_code if response else None
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def _get_position_state(client: AsterFuturesClient, symbol: str) -> Dict:
    """
    Get current position state.
    
    Returns:
        Dictionary with position info: has_position, direction, quantity, etc.
    """
    positions = client.get_positions(symbol)
    if not positions:
        return {
            "has_position": False,
            "direction": None,
            "quantity": 0,
            "entry_price": 0,
            "unrealized_profit": 0
        }
    
    pos = positions[0]
    position_amt = pos["position_amt"]
    
    return {
        "has_position": position_amt != 0,
        "direction": "LONG" if position_amt > 0 else ("SHORT" if position_amt < 0 else None),
        "quantity": abs(position_amt),
        "entry_price": pos["entry_price"],
        "unrealized_profit": pos["unrealized_profit"],
        "mark_price": pos["mark_price"]
    }


def _place_sl_tp_with_retry(
    client: AsterFuturesClient,
    symbol: str,
    side: str,
    quantity: float,
    stop_loss_price: Optional[float],
    take_profit_price: Optional[float],
    max_retries: int = 3
) -> Dict:
    """
    Place SL/TP orders with retry logic.
    
    Returns:
        Result dictionary with order IDs or error info.
    """
    result = {"stop_loss": None, "take_profit": None, "errors": []}
    
    for attempt in range(max_retries):
        try:
            sl_tp_result = client.place_sl_tp_orders(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trigger_type="MARK_PRICE"
            )
            result["stop_loss"] = sl_tp_result.get("stop_loss")
            result["take_profit"] = sl_tp_result.get("take_profit")
            return result
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
            result["errors"].append(error_msg)
            if attempt < max_retries - 1:
                import time
                time.sleep(1)  # Wait before retry
            else:
                result["final_error"] = f"Failed after {max_retries} attempts"
    
    return result


@tool
def open_long_position(
    symbol: str,
    position_size_usd: float,
    leverage: int,
    entry_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None
) -> str:
    """
    Open a long position with intelligent order management.
    
    Supports:
    - Adding to existing long positions
    - Switching from short to long (auto-closes short first)
    - Automatic SL/TP order management with retry
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT".
        position_size_usd: Position notional in USD.
        leverage: Leverage multiplier.
        entry_price: Optional limit entry price (None for market orders).
        stop_loss_price: Optional stop-loss price.
        take_profit_price: Optional take-profit price.
        
    Returns:
        JSON string describing the order result.
    """
    try:
        client = get_futures_client()
        adjustments = []
        
        # 1. Check current position state
        current_state = _get_position_state(client, symbol)
        
        # 2. Handle opposite position (SHORT → LONG)
        if current_state["has_position"] and current_state["direction"] == "SHORT":
            adjustments.append(f"Detected SHORT position, closing it before opening LONG")
            close_result = client.close_position(symbol, percent=100.0)
            adjustments.append(f"Closed SHORT position: {close_result.get('message', 'Success')}")
            
            # Wait briefly for position to close
            import time
            time.sleep(1)
            
            # Verify position is closed
            updated_state = _get_position_state(client, symbol)
            if updated_state["has_position"]:
                return json.dumps({
                    "error": "Failed to close opposite SHORT position",
                    "current_position": updated_state
                })
            
            # Safe to cancel all orders now (no position to protect)
            client.cancel_all_orders(symbol)
            adjustments.append("Cancelled all orders after closing opposite position")
        
        # 3. If no position exists, clean up any stale orders
        elif not current_state["has_position"]:
            try:
                client.cancel_all_orders(symbol)
                adjustments.append("Cancelled stale orders (no position to protect)")
            except Exception as e:
                adjustments.append(f"Note: Could not cancel orders: {str(e)}")
        
        # 4. Fetch current price (used for quantity calculation)
        mark_data = client.get_mark_price(symbol)
        current_price = entry_price if entry_price else mark_data["mark_price"]
        
        if current_price <= 0:
            return json.dumps({"error": "Invalid current price returned by exchange"})
        
        filters = client.get_symbol_filters(symbol)
        min_qty = filters.get("min_qty", 0.0)
        step_size = filters.get("step_size", 0.0)
        min_notional = filters.get("min_notional", 0.0)
        
        # 5. Compute quantity and satisfy exchange minimums
        quantity = position_size_usd / current_price if position_size_usd > 0 else 0.0
        
        min_qty_from_notional = (min_notional / current_price) if (min_notional and current_price > 0) else 0.0
        target_qty = max(quantity, min_qty, min_qty_from_notional)
        
        if target_qty > quantity:
            adjustments.append(
                f"Quantity raised to minimum tradable size ({target_qty:.6f}) to satisfy exchange filters"
            )
        quantity = target_qty
        
        if step_size and step_size > 0:
            quantity = math.ceil(quantity / step_size) * step_size
        
        if quantity <= 0:
            return json.dumps({"error": "Unable to determine a valid trade quantity"})
        
        # Update notional size after adjustments
        adjusted_notional = quantity * current_price
        
        # 3. Check leverage and available balance constraints
        account_info = client.get_account()
        available_balance = account_info.get("available_balance", 0.0)
        
        if available_balance <= 0:
            return json.dumps({"error": "Insufficient available balance"})
        
        required_margin = adjusted_notional / max(leverage, 1)
        if required_margin > available_balance:
            min_leverage = math.ceil(adjusted_notional / available_balance)
            if min_leverage > 125:
                return json.dumps({
                    "error": "Insufficient balance for minimum order size even at max leverage",
                    "required_notional": adjusted_notional,
                    "available_balance": available_balance,
                    "min_leverage_needed": min_leverage
                })
            if min_leverage > leverage:
                leverage = min_leverage
                adjustments.append(f"Leverage increased to {leverage}x to satisfy minimum margin requirements")
        
        # 5. Apply leverage setting
        client.set_leverage(symbol, leverage)
        
        # 6. Validate and adjust parameters
        validation = client.validate_order_params(symbol, current_price, quantity)
        if not validation["valid"]:
            return json.dumps({"error": "Order validation failed", "details": validation["errors"]})
        
        quantity = validation["adjusted_quantity"]
        adjusted_notional = quantity * validation["adjusted_price"]
        
        # 7. Submit entry order
        order_type = "LIMIT" if entry_price else "MARKET"
        client_order_id = f"long_open_{uuid.uuid4().hex[:8]}"
        
        order = client.place_order(
            symbol=symbol,
            side="BUY",
            order_type=order_type,
            quantity=quantity,
            price=entry_price,
            client_order_id=client_order_id,
        )
        
        # 8. Get updated position (might include previous position + new order)
        import time
        time.sleep(0.5)  # Brief wait for order to be processed
        final_state = _get_position_state(client, symbol)
        total_quantity = final_state["quantity"]
        old_quantity = current_state.get("quantity", 0)
        
        if total_quantity <= 0:
            # Fallback if position not updated yet
            total_quantity = quantity
        
        # 9. Update SL/TP based on position change
        # Key insight: Always update SL/TP to match ACTUAL position size
        # This protects against the risk window when limit orders fill between cycles
        sl_tp_result = None
        position_changed = abs(total_quantity - old_quantity) > 0.0001
        
        if position_changed:
            # Position size changed (order filled), update SL/TP to match
            try:
                open_orders = client.get_open_orders(symbol)
                cancelled_count = 0
                for order in open_orders:
                    if order.get("reduceOnly"):  # Only cancel protective orders (SL/TP)
                        try:
                            client.cancel_order(symbol, order["orderId"])
                            cancelled_count += 1
                        except:
                            pass
                adjustments.append(f"Cancelled {cancelled_count} old protective orders (position changed: {old_quantity:.4f} -> {total_quantity:.4f})")
            except Exception as e:
                adjustments.append(f"Warning: Could not cancel old orders: {str(e)}")
                
            # 10. Place SL/TP for TOTAL position with retry logic
            if stop_loss_price or take_profit_price:
                adjustments.append(f"Placing SL/TP for total quantity: {total_quantity}")
                sl_tp_result = _place_sl_tp_with_retry(
                    client=client,
                    symbol=symbol,
                    side="SELL",  # Close long position
                    quantity=total_quantity,  # Use TOTAL position quantity
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    max_retries=3
                )
            
                if sl_tp_result.get("errors"):
                    for error in sl_tp_result["errors"]:
                        adjustments.append(f"SL/TP retry: {error}")
        else:
            # Position unchanged (limit order not filled yet), keep existing SL/TP
            adjustments.append(f"Position unchanged ({total_quantity:.4f}), existing SL/TP unchanged")
        
        result = {
            "success": True,
            "action": "OPEN_LONG",
            "symbol": symbol,
            "order_id": order.get("orderId"),
            "client_order_id": client_order_id,
            "new_order_quantity": quantity,
            "total_position_quantity": total_quantity,
            "entry_price": entry_price or "MARKET",
            "leverage": leverage,
            "new_order_notional": adjusted_notional,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "had_previous_position": current_state["has_position"],
            "previous_direction": current_state["direction"]
        }
        
        # Include SL/TP order IDs if successfully placed
        if sl_tp_result:
            if sl_tp_result.get("stop_loss"):
                result["stop_loss_order_id"] = sl_tp_result["stop_loss"].get("orderId")
            if sl_tp_result.get("take_profit"):
                result["take_profit_order_id"] = sl_tp_result["take_profit"].get("orderId")
            if sl_tp_result.get("final_error"):
                result["sl_tp_warning"] = sl_tp_result["final_error"]
        
        if adjustments:
            result["adjustments"] = adjustments
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def open_short_position(
    symbol: str,
    position_size_usd: float,
    leverage: int,
    entry_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None
) -> str:
    """
    Open a short position with intelligent order management.
    
    Supports:
    - Adding to existing short positions
    - Switching from long to short (auto-closes long first)
    - Automatic SL/TP order management with retry
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT".
        position_size_usd: Position notional in USD.
        leverage: Leverage multiplier.
        entry_price: Optional limit entry price (None for market orders).
        stop_loss_price: Optional stop-loss price.
        take_profit_price: Optional take-profit price.
        
    Returns:
        JSON string describing the order result.
    """
    try:
        client = get_futures_client()
        adjustments = []
        
        # 1. Check current position state
        current_state = _get_position_state(client, symbol)
        
        # 2. Handle opposite position (LONG → SHORT)
        if current_state["has_position"] and current_state["direction"] == "LONG":
            adjustments.append(f"Detected LONG position, closing it before opening SHORT")
            close_result = client.close_position(symbol, percent=100.0)
            adjustments.append(f"Closed LONG position: {close_result.get('message', 'Success')}")
            
            # Wait briefly for position to close
            import time
            time.sleep(1)
            
            # Verify position is closed
            updated_state = _get_position_state(client, symbol)
            if updated_state["has_position"]:
                return json.dumps({
                    "error": "Failed to close opposite LONG position",
                    "current_position": updated_state
                })
            
            # Safe to cancel all orders now (no position to protect)
            client.cancel_all_orders(symbol)
            adjustments.append("Cancelled all orders after closing opposite position")
        
        # 3. If no position exists, clean up any stale orders
        elif not current_state["has_position"]:
            try:
                client.cancel_all_orders(symbol)
                adjustments.append("Cancelled stale orders (no position to protect)")
            except Exception as e:
                adjustments.append(f"Note: Could not cancel orders: {str(e)}")
        
        # 4. Fetch current price (used for quantity calculation)
        mark_data = client.get_mark_price(symbol)
        current_price = entry_price if entry_price else mark_data["mark_price"]
        
        if current_price <= 0:
            return json.dumps({"error": "Invalid current price returned by exchange"})
        
        filters = client.get_symbol_filters(symbol)
        min_qty = filters.get("min_qty", 0.0)
        step_size = filters.get("step_size", 0.0)
        min_notional = filters.get("min_notional", 0.0)
        
        quantity = position_size_usd / current_price if position_size_usd > 0 else 0.0
        adjustments = []
        
        min_qty_from_notional = (min_notional / current_price) if (min_notional and current_price > 0) else 0.0
        target_qty = max(quantity, min_qty, min_qty_from_notional)
        
        if target_qty > quantity:
            adjustments.append(
                f"Quantity raised to minimum tradable size ({target_qty:.6f}) to satisfy exchange filters"
            )
        quantity = target_qty
        
        if step_size and step_size > 0:
            quantity = math.ceil(quantity / step_size) * step_size
        
        if quantity <= 0:
            return json.dumps({"error": "Unable to determine a valid trade quantity"})
        
        adjusted_notional = quantity * current_price
        
        account_info = client.get_account()
        available_balance = account_info.get("available_balance", 0.0)
        
        if available_balance <= 0:
            return json.dumps({"error": "Insufficient available balance"})
        
        required_margin = adjusted_notional / max(leverage, 1)
        if required_margin > available_balance:
            min_leverage = math.ceil(adjusted_notional / available_balance)
            if min_leverage > 125:
                return json.dumps({
                    "error": "Insufficient balance for minimum order size even at max leverage",
                    "required_notional": adjusted_notional,
                    "available_balance": available_balance,
                    "min_leverage_needed": min_leverage
                })
            if min_leverage > leverage:
                leverage = min_leverage
                adjustments.append(f"Leverage increased to {leverage}x to satisfy minimum margin requirements")
        
        # 5. Apply leverage setting
        client.set_leverage(symbol, leverage)
        
        # 6. Validate and adjust parameters
        validation = client.validate_order_params(symbol, current_price, quantity)
        if not validation["valid"]:
            return json.dumps({"error": "Order validation failed", "details": validation["errors"]})
        
        quantity = validation["adjusted_quantity"]
        adjusted_notional = quantity * validation["adjusted_price"]
        
        # 7. Submit entry order
        order_type = "LIMIT" if entry_price else "MARKET"
        client_order_id = f"short_open_{uuid.uuid4().hex[:8]}"
        
        order = client.place_order(
            symbol=symbol,
            side="SELL",
            order_type=order_type,
            quantity=quantity,
            price=entry_price,
            client_order_id=client_order_id,
        )
        
        # 8. Get updated position (might include previous position + new order)
        import time
        time.sleep(0.5)  # Brief wait for order to be processed
        final_state = _get_position_state(client, symbol)
        total_quantity = final_state["quantity"]
        old_quantity = current_state.get("quantity", 0)
        
        if total_quantity <= 0:
            # Fallback if position not updated yet
            total_quantity = quantity
        
        # 9. Update SL/TP based on position change
        # Key insight: Always update SL/TP to match ACTUAL position size
        # This protects against the risk window when limit orders fill between cycles
        sl_tp_result = None
        position_changed = abs(total_quantity - old_quantity) > 0.0001
        
        if position_changed:
            # Position size changed (order filled), update SL/TP to match
            try:
                open_orders = client.get_open_orders(symbol)
                cancelled_count = 0
                for order in open_orders:
                    if order.get("reduceOnly"):  # Only cancel protective orders (SL/TP)
                        try:
                            client.cancel_order(symbol, order["orderId"])
                            cancelled_count += 1
                        except:
                            pass
                adjustments.append(f"Cancelled {cancelled_count} old protective orders (position changed: {old_quantity:.4f} -> {total_quantity:.4f})")
            except Exception as e:
                adjustments.append(f"Warning: Could not cancel old orders: {str(e)}")
                
            # 10. Place SL/TP for TOTAL position with retry logic
            if stop_loss_price or take_profit_price:
                adjustments.append(f"Placing SL/TP for total quantity: {total_quantity}")
                sl_tp_result = _place_sl_tp_with_retry(
                    client=client,
                    symbol=symbol,
                    side="BUY",  # Close short position
                    quantity=total_quantity,  # Use TOTAL position quantity
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    max_retries=3
                )
            
                if sl_tp_result.get("errors"):
                    for error in sl_tp_result["errors"]:
                        adjustments.append(f"SL/TP retry: {error}")
        else:
            # Position unchanged (limit order not filled yet), keep existing SL/TP
            adjustments.append(f"Position unchanged ({total_quantity:.4f}), existing SL/TP unchanged")
        
        result = {
            "success": True,
            "action": "OPEN_SHORT",
            "symbol": symbol,
            "order_id": order.get("orderId"),
            "client_order_id": client_order_id,
            "new_order_quantity": quantity,
            "total_position_quantity": total_quantity,
            "entry_price": entry_price or "MARKET",
            "leverage": leverage,
            "new_order_notional": adjusted_notional,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "had_previous_position": current_state["has_position"],
            "previous_direction": current_state["direction"]
        }
        
        # Include SL/TP order IDs if successfully placed
        if sl_tp_result:
            if sl_tp_result.get("stop_loss"):
                result["stop_loss_order_id"] = sl_tp_result["stop_loss"].get("orderId")
            if sl_tp_result.get("take_profit"):
                result["take_profit_order_id"] = sl_tp_result["take_profit"].get("orderId")
            if sl_tp_result.get("final_error"):
                result["sl_tp_warning"] = sl_tp_result["final_error"]
        
        if adjustments:
            result["adjustments"] = adjustments
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def close_position(symbol: str, percent: float = 100.0) -> str:
    """
    Close an existing position and clean up all protective orders.
    
    This function performs two critical steps:
    1. Cancel all reduce-only orders (SL/TP) to prevent orphaned orders
    2. Execute market order to close the position
    
    Args:
        symbol: Trading pair.
        percent: Percentage to close (0-100, default 100 for full close).
        
    Returns:
        JSON string describing the close result.
    """
    try:
        if percent <= 0 or percent > 100:
            return json.dumps({"error": "Percent must be between 0 and 100"})
        
        client = get_futures_client()
        
        # Step 1: Cancel all reduce-only orders (SL/TP) before closing position
        # This prevents orphaned orders that would be useless after position is closed
        cancelled_orders = 0
        try:
            open_orders = client.get_open_orders(symbol)
            for order in open_orders:
                if order.get("reduceOnly"):
                    try:
                        client.cancel_order(symbol, order["orderId"])
                        cancelled_orders += 1
                        logger.debug(f"Cancelled protective order {order['orderId']} before closing position")
                    except Exception as e:
                        logger.warning(f"Failed to cancel order {order['orderId']}: {e}")
            
            if cancelled_orders > 0:
                logger.info(f"Cancelled {cancelled_orders} protective orders before closing position")
        except Exception as e:
            logger.warning(f"Error while cancelling protective orders: {e}")
            # Continue to close position even if order cancellation fails
        
        # Step 2: Execute market order to close the position
        result = client.close_position(symbol, percent)
        
        return json.dumps({
            "success": True,
            "action": "CLOSE_POSITION",
            "symbol": symbol,
            "percent": percent,
            "cancelled_orders": cancelled_orders,
            "result": result
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def update_sl_tp(
    symbol: str,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None
) -> str:
    """
    Update stop-loss and take-profit orders.
    
    Existing protective orders are cancelled before submitting new ones.
    
    Args:
        symbol: Trading pair.
        stop_loss_price: Optional new stop-loss price.
        take_profit_price: Optional new take-profit price.
        
    Returns:
        JSON string describing the update result.
    """
    try:
        client = get_futures_client()
        
        # 1. Fetch current position
        positions = client.get_positions(symbol)
        if not positions:
            return json.dumps({"error": f"No position for {symbol}"})
        
        pos = positions[0]
        quantity = abs(pos["position_amt"])
        side = "SELL" if pos["position_amt"] > 0 else "BUY"  # Closing direction
        
        # 2. Cancel all working orders (including old SL/TP)
        client.cancel_all_orders(symbol)
        
        # 3. Submit new SL/TP orders
        result = client.place_sl_tp_orders(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            trigger_type="MARK_PRICE"
        )
        
        return json.dumps({
            "success": True,
            "action": "UPDATE_SL_TP",
            "symbol": symbol,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "orders": result
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


def _extract_protective_orders(orders: List[Dict]) -> tuple:
    """
    Extract existing stop-loss and take-profit prices from orders.
    
    Args:
        orders: List of open orders
        
    Returns:
        Tuple of (stop_loss_price, take_profit_price)
    """
    stop_loss_price = None
    take_profit_price = None
    
    for order in orders:
        if not order.get("reduceOnly"):
            continue
            
        order_type = order.get("type")
        stop_price = float(order.get("stopPrice", 0))
        
        if order_type == "STOP_MARKET" and stop_price > 0:
            stop_loss_price = stop_price
        elif order_type == "TAKE_PROFIT_MARKET" and stop_price > 0:
            take_profit_price = stop_price
    
    return stop_loss_price, take_profit_price


def _in_danger_zone(
    current_price: float,
    existing_sl: Optional[float],
    existing_tp: Optional[float],
    sl_threshold: float = 0.005,  # 0.5%
    tp_threshold: float = 0.002   # 0.2%
) -> tuple:
    """
    Check if current price is dangerously close to protective orders.
    
    Args:
        current_price: Current market price
        existing_sl: Existing stop-loss price
        existing_tp: Existing take-profit price
        sl_threshold: Stop-loss danger threshold (default 0.5%)
        tp_threshold: Take-profit danger threshold (default 0.2%)
        
    Returns:
        Tuple of (is_dangerous, reason)
    """
    if existing_sl and existing_sl > 0:
        distance_to_sl = abs(current_price - existing_sl) / current_price
        if distance_to_sl < sl_threshold:
            return True, f"Price within {sl_threshold*100}% of stop-loss ({current_price} vs {existing_sl})"
    
    if existing_tp and existing_tp > 0:
        distance_to_tp = abs(current_price - existing_tp) / current_price
        if distance_to_tp < tp_threshold:
            return True, f"Price within {tp_threshold*100}% of take-profit ({current_price} vs {existing_tp})"
    
    return False, "Safe distance from protective orders"


def _is_trailing_stop_valid(
    position_side: str,
    existing_sl: Optional[float],
    new_sl: Optional[float],
    current_price: float
) -> tuple:
    """
    Validate that the new stop-loss follows trailing stop rules (only moves favorably).
    
    This is a CRITICAL safety mechanism to prevent "riding losses" (扛单).
    
    Rules:
    - For LONG positions: New SL can only be >= existing SL (moving up, tighter stop)
    - For SHORT positions: New SL can only be <= existing SL (moving down, tighter stop)
    
    Args:
        position_side: "LONG" or "SHORT"
        existing_sl: Current stop-loss price (None if no existing SL)
        new_sl: Proposed new stop-loss price
        current_price: Current market price
        
    Returns:
        Tuple of (is_valid, reason)
    """
    # If no new SL is being set, or no existing SL to compare, allow it
    if not new_sl:
        return True, "No new stop-loss being set"
    
    if not existing_sl or existing_sl == 0:
        return True, "No existing stop-loss to compare against (initial SL setup)"
    
    # Check if SL is moving in the correct direction
    if position_side == "LONG":
        # For LONG: SL should only move UP (towards or above current price)
        # This tightens the stop, protecting profits or limiting losses
        if new_sl < existing_sl:
            return False, f"Invalid SL move for LONG: new SL ${new_sl:.2f} is LOWER than existing SL ${existing_sl:.2f}. This would INCREASE risk. Stop-loss can only be raised, never lowered."
    
    elif position_side == "SHORT":
        # For SHORT: SL should only move DOWN (towards or below current price)
        # This tightens the stop, protecting profits or limiting losses
        if new_sl > existing_sl:
            return False, f"Invalid SL move for SHORT: new SL ${new_sl:.2f} is HIGHER than existing SL ${existing_sl:.2f}. This would INCREASE risk. Stop-loss can only be lowered, never raised."
    
    return True, "Valid trailing stop move"


def _prices_match(
    existing_sl: Optional[float],
    existing_tp: Optional[float],
    new_sl: Optional[float],
    new_tp: Optional[float],
    existing_orders: List[Dict] = None,
    expected_quantity: float = 0,
    threshold: float = 0.001  # 0.1%
) -> tuple:
    """
    Check if new prices match existing ones within threshold AND quantities match position.
    
    Args:
        existing_sl: Current stop-loss price
        existing_tp: Current take-profit price
        new_sl: New stop-loss price
        new_tp: New take-profit price
        existing_orders: List of existing orders to check quantities
        expected_quantity: Expected quantity that SL/TP should protect
        threshold: Matching threshold (default 0.1%)
        
    Returns:
        Tuple of (prices_match, reason)
    """
    sl_matches = True
    tp_matches = True
    qty_matches = True
    reasons = []
    
    # Check stop-loss price
    if new_sl and existing_sl and existing_sl > 0:
        sl_diff_pct = abs(new_sl - existing_sl) / existing_sl
        if sl_diff_pct > threshold:
            sl_matches = False
            reasons.append(f"SL price differs by {sl_diff_pct*100:.2f}% ({existing_sl} -> {new_sl})")
    elif new_sl and not existing_sl:
        sl_matches = False
        reasons.append(f"SL missing, needs to be set to {new_sl}")
    
    # Check take-profit price
    if new_tp and existing_tp and existing_tp > 0:
        tp_diff_pct = abs(new_tp - existing_tp) / existing_tp
        if tp_diff_pct > threshold:
            tp_matches = False
            reasons.append(f"TP price differs by {tp_diff_pct*100:.2f}% ({existing_tp} -> {new_tp})")
    elif new_tp and not existing_tp:
        tp_matches = False
        reasons.append(f"TP missing, needs to be set to {new_tp}")
    
    # Check quantities match position size
    if existing_orders and expected_quantity > 0:
        existing_sl_qty = 0
        existing_tp_qty = 0
        
        for order in existing_orders:
            if order.get("reduceOnly"):
                qty = float(order.get("origQty", 0))
                order_type = order.get("type", "")
                
                if order_type == "STOP_MARKET":
                    existing_sl_qty = qty
                elif order_type == "TAKE_PROFIT_MARKET":
                    existing_tp_qty = qty
        
        # Check if SL quantity matches
        if existing_sl_qty > 0:
            if abs(existing_sl_qty - expected_quantity) / expected_quantity > 0.01:  # 1% tolerance
                qty_matches = False
                reasons.append(f"SL quantity mismatch: {existing_sl_qty:.4f} vs position {expected_quantity:.4f}")
        else:
            qty_matches = False
            reasons.append(f"SL order missing (position: {expected_quantity:.4f})")
        
        # Check if TP quantity matches
        if existing_tp_qty > 0:
            if abs(existing_tp_qty - expected_quantity) / expected_quantity > 0.01:  # 1% tolerance
                qty_matches = False
                reasons.append(f"TP quantity mismatch: {existing_tp_qty:.4f} vs position {expected_quantity:.4f}")
        else:
            qty_matches = False
            reasons.append(f"TP order missing (position: {expected_quantity:.4f})")
    
    if sl_matches and tp_matches and qty_matches:
        return True, "Prices and quantities already optimal"
    else:
        return False, "; ".join(reasons)


@tool
def update_sl_tp_safe(
    symbol: str,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None
) -> str:
    """
    Safely update stop-loss and take-profit orders with built-in safety checks.
    
    This tool automatically handles:
    - Danger zone detection: Won't update if price is too close to existing protective orders
    - Price matching: Won't update if prices are already optimal (within 0.1% tolerance)
    - Atomic updates: Creates new orders before cancelling old ones to prevent exposure
    - Edge case handling: Manages missing orders, network failures, etc.
    - Value preservation: If a parameter is None, the existing value is preserved
    
    Safety thresholds:
    - Stop-loss danger zone: 0.5% (won't update if price within 0.5% of SL)
    - Take-profit danger zone: 0.2% (won't update if price within 0.2% of TP)
    - Price matching tolerance: 0.1% (considers prices "same" if within 0.1%)
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT"
        stop_loss_price: New stop-loss price (None = keep existing SL unchanged)
        take_profit_price: New take-profit price (None = keep existing TP unchanged)
        
    Returns:
        JSON string with action taken ("updated", "skipped", or "error") and detailed reason
    """
    try:
        client = get_futures_client()
        
        # 1. Fetch current position
        positions = client.get_positions(symbol)
        if not positions:
            return json.dumps({
                "action": "error",
                "reason": f"No position exists for {symbol}"
            }, indent=2)
        
        pos = positions[0]
        position_amt = float(pos["position_amt"])
        
        if abs(position_amt) == 0:
            return json.dumps({
                "action": "error",
                "reason": f"Position size is zero for {symbol}"
            }, indent=2)
        
        quantity = abs(position_amt)
        current_price = float(pos["mark_price"])
        side = "SELL" if position_amt > 0 else "BUY"
        position_side = "LONG" if position_amt > 0 else "SHORT"
        
        # 2. Fetch existing orders
        open_orders = client.get_open_orders(symbol)
        existing_sl, existing_tp = _extract_protective_orders(open_orders)
        
        # 3. SAFETY CHECK 1: Trailing stop validation (CRITICAL - prevents riding losses)
        is_valid_trailing, trailing_reason = _is_trailing_stop_valid(
            position_side, existing_sl, stop_loss_price, current_price
        )
        if not is_valid_trailing:
            return json.dumps({
                "action": "rejected",
                "reason": f"TRAILING STOP VIOLATION: {trailing_reason}",
                "safety_note": "Stop-loss can ONLY move in a favorable direction (trailing stop). Moving it in an unfavorable direction would increase risk and is FORBIDDEN.",
                "details": {
                    "position_side": position_side,
                    "current_price": current_price,
                    "existing_stop_loss": existing_sl,
                    "requested_stop_loss": stop_loss_price,
                    "existing_take_profit": existing_tp
                }
            }, indent=2)
        
        # 4. SAFETY CHECK 2: Danger zone detection
        is_dangerous, danger_reason = _in_danger_zone(current_price, existing_sl, existing_tp)
        if is_dangerous:
            return json.dumps({
                "action": "skipped",
                "reason": f"DANGER ZONE: {danger_reason}",
                "details": {
                    "current_price": current_price,
                    "existing_stop_loss": existing_sl,
                    "existing_take_profit": existing_tp,
                    "requested_stop_loss": stop_loss_price,
                    "requested_take_profit": take_profit_price
                },
                "safety_note": "Not updating orders because price is too close to triggers. Let existing orders execute."
            }, indent=2)
        
        # 5. SAFETY CHECK 3: Price and quantity matching
        prices_match, match_reason = _prices_match(
            existing_sl, existing_tp, stop_loss_price, take_profit_price,
            existing_orders=open_orders,
            expected_quantity=quantity
        )
        if prices_match:
            return json.dumps({
                "action": "skipped",
                "reason": f"ALREADY OPTIMAL: {match_reason}",
                "details": {
                    "current_price": current_price,
                    "existing_stop_loss": existing_sl,
                    "existing_take_profit": existing_tp,
                    "requested_stop_loss": stop_loss_price,
                    "requested_take_profit": take_profit_price
                }
            }, indent=2)
        
        # 6. ATOMIC UPDATE: Create new orders first, then cancel old ones
        # IMPORTANT: If None is passed, preserve existing value (don't remove it)
        final_sl = stop_loss_price if stop_loss_price is not None else existing_sl
        final_tp = take_profit_price if take_profit_price is not None else existing_tp
        
        logger.info(f"Updating SL/TP for {symbol}: SL {existing_sl}->{final_sl}, TP {existing_tp}->{final_tp}")
        
        # Step 6a: Create new protective orders
        try:
            new_orders = client.place_sl_tp_orders(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_loss_price=final_sl,
                take_profit_price=final_tp,
                trigger_type="MARK_PRICE"
            )
        except Exception as e:
            # If creating new orders fails, old orders remain intact (SAFE!)
            return json.dumps({
                "action": "error",
                "reason": f"Failed to create new orders: {str(e)}",
                "safety_note": "Old protective orders remain intact - position is still protected",
                "details": {
                    "existing_stop_loss": existing_sl,
                    "existing_take_profit": existing_tp
                }
            }, indent=2)
        
        # Step 6b: Only cancel old protective orders after new ones are successfully created
        # Important: Cancel ONLY old reduce-only orders, not the newly created ones
        cancelled_count = 0
        try:
            for order in open_orders:
                if order.get("reduceOnly"):
                    try:
                        client.cancel_order(symbol, order["orderId"])
                        cancelled_count += 1
                        logger.debug(f"Cancelled old protective order {order['orderId']}")
                    except Exception as e:
                        logger.warning(f"Failed to cancel old order {order['orderId']}: {e}")
            logger.info(f"Cancelled {cancelled_count} old protective orders")
        except Exception as e:
            logger.warning(f"Error while cancelling old orders: {e}")
        
        return json.dumps({
            "action": "updated",
            "reason": match_reason,
            "details": {
                "current_price": current_price,
                "old_stop_loss": existing_sl,
                "new_stop_loss": final_sl,
                "old_take_profit": existing_tp,
                "new_take_profit": final_tp,
                "position_quantity": quantity,
                "position_side": "LONG" if position_amt > 0 else "SHORT"
            },
            "orders": new_orders
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "action": "error",
            "reason": f"Unexpected error: {str(e)}"
        }, indent=2)


@tool
def reduce_position(symbol: str, reduce_pct: float) -> str:
    """
    Reduce an open position by percentage and automatically adjust SL/TP orders.
    
    This function performs:
    1. Get existing SL/TP prices before reduction
    2. Execute market order to reduce position
    3. Wait for order execution
    4. Automatically update SL/TP orders with new quantities
    
    Args:
        symbol: Trading pair.
        reduce_pct: Reduction percentage (0-100).
        
    Returns:
        JSON string describing the reduce result and SL/TP adjustments.
    """
    try:
        if reduce_pct <= 0 or reduce_pct > 100:
            return json.dumps({"error": "reduce_pct must be between 0 and 100"})
        
        client = get_futures_client()
        
        # Fetch the current position
        positions = client.get_positions(symbol)
        if not positions:
            return json.dumps({"error": f"No position for {symbol}"})
        
        pos = positions[0]
        position_amt = pos["position_amt"]
        reduce_qty = abs(position_amt) * (reduce_pct / 100.0)
        
        # Get existing SL/TP prices before reducing
        open_orders = client.get_open_orders(symbol)
        existing_sl, existing_tp = _extract_protective_orders(open_orders)
        
        # Determine the closing direction
        side = "SELL" if position_amt > 0 else "BUY"
        
        # Submit a reduce-only market order
        # Note: Old SL/TP orders remain active during this process (by design)
        # This ensures the position is ALWAYS protected, even if subsequent steps fail
        # The exchange's reduceOnly mechanism prevents over-closing even if quantities don't match
        client_order_id = f"reduce_{uuid.uuid4().hex[:8]}"
        order = client.place_order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=reduce_qty,
            reduce_only=True,
            client_order_id=client_order_id
        )
        
        # Wait briefly for order execution
        time.sleep(0.5)
        
        # Adjust SL/TP orders to match new position size (after successful reduction)
        sl_tp_update = None
        if existing_sl or existing_tp:
            try:
                # Get new position size after reduction
                new_positions = client.get_positions(symbol)
                if new_positions and abs(float(new_positions[0]["position_amt"])) > 0:
                    new_qty = abs(float(new_positions[0]["position_amt"]))
                    
                    # Cancel old SL/TP orders (now with incorrect quantities)
                    cancelled_orders = 0
                    for ord in open_orders:
                        if ord.get("reduceOnly"):
                            try:
                                client.cancel_order(symbol, ord["orderId"])
                                cancelled_orders += 1
                            except Exception as e:
                                logger.warning(f"Failed to cancel old order {ord['orderId']}: {e}")
                    
                    # Create new SL/TP with correct quantities
                    sl_tp_result = client.place_sl_tp_orders(
                        symbol=symbol,
                        side=side,
                        quantity=new_qty,
                        stop_loss_price=existing_sl,
                        take_profit_price=existing_tp,
                        trigger_type="MARK_PRICE"
                    )
                    sl_tp_update = {
                        "adjusted": True,
                        "new_quantity": new_qty,
                        "old_quantity": abs(position_amt),
                        "cancelled_orders": cancelled_orders,
                        "stop_loss": existing_sl,
                        "take_profit": existing_tp
                    }
                    logger.info(f"Adjusted SL/TP after reducing position by {reduce_pct}% (qty: {abs(position_amt):.4f} -> {new_qty:.4f})")
            except Exception as e:
                sl_tp_update = {"adjusted": False, "error": str(e)}
                logger.warning(f"Failed to adjust SL/TP after reduction: {e}")
                logger.info(f"Old SL/TP orders remain active - position is still protected (reduceOnly prevents over-closing)")
        
        return json.dumps({
            "success": True,
            "action": "REDUCE_POSITION",
            "symbol": symbol,
            "reduce_pct": reduce_pct,
            "reduce_qty": reduce_qty,
            "order_id": order.get("orderId"),
            "client_order_id": client_order_id,
            "sl_tp_adjustment": sl_tp_update
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def cancel_order(symbol: str, order_id: int) -> str:
    """
    Cancel a specific order by order ID.
    
    Use this when you need to cancel a single order (e.g., after getting order details from get_open_orders).
    
    Args:
        symbol: Trading pair, e.g., "BTCUSDT".
        order_id: The order ID to cancel (get from get_open_orders).
        
    Returns:
        JSON string describing the cancellation result.
    """
    try:
        client = get_futures_client()
        result = client.cancel_order(symbol, order_id=order_id)
        
        return json.dumps({
            "success": True,
            "action": "CANCEL_ORDER",
            "symbol": symbol,
            "order_id": order_id,
            "result": result
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def cancel_all_orders_for_symbol(symbol: str) -> str:
    """
    Cancel all open orders for a symbol.
    
    Use this when you want to clear all pending orders at once (more aggressive than cancel_order).
    
    Args:
        symbol: Trading pair.
        
    Returns:
        JSON string describing the cancellation.
    """
    try:
        client = get_futures_client()
        result = client.cancel_all_orders(symbol)
        
        return json.dumps({
            "success": True,
            "action": "CANCEL_ALL_ORDERS",
            "symbol": symbol,
            "result": result
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def prepare_trading_environment(
    symbol: str,
    new_action: str,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None
) -> str:
    """
    Prepare a safe trading environment by executing all deterministic pre-trade checks.
    
    This tool automatically handles:
    1. Get current trading status (position, orders, account)
    2. Verify and fix SL/TP protection if needed
    3. Clean up stale orders based on the new action
    
    The Agent should:
    - Call this tool first before any trading action
    - Review the returned status and warnings
    - Decide whether to proceed based on the 'ready' flag and warnings
    
    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        new_action: Planned action from portfolio plan ("LONG" | "SHORT" | "HOLD" | "EXIT" | "REDUCE")
        stop_loss_price: Stop-loss price from portfolio plan
        take_profit_price: Take-profit price from portfolio plan
        
    Returns:
        JSON string with:
        - ready: boolean (true if environment is safe to proceed)
        - status: current position and account info
        - actions_taken: list of what was fixed/cleaned
        - warnings: list of issues that need Agent attention
        - recommendation: suggested next step
    """
    try:
        client = get_futures_client()
        actions_taken = []
        warnings = []
        
        # ═══════════════════════════════════════
        # Step 1: Get current status
        # ═══════════════════════════════════════
        logger.info(f"Preparing trading environment for {symbol}, action: {new_action}")
        
        positions = client.get_positions(symbol)
        
        # Handle position status - empty list means no position (normal case)
        if positions and len(positions) > 0:
            pos = positions[0]
            position_amt = float(pos.get("position_amt", 0))
            has_position = abs(position_amt) > 0.0001
            current_direction = "LONG" if position_amt > 0 else "SHORT" if position_amt < 0 else None
        else:
            # No position - this is normal when starting fresh
            has_position = False
            position_amt = 0
            current_direction = None
        
        # Get open orders
        open_orders = client.get_open_orders(symbol)
        
        # ═══════════════════════════════════════
        # Step 2: Check and fix SL/TP protection
        # ═══════════════════════════════════════
        if has_position and (stop_loss_price or take_profit_price):
            # Check current protection status
            existing_sl, existing_tp = _extract_protective_orders(open_orders)
            quantity = abs(position_amt)
            
            # Check if protection needs update
            sl_qty = 0
            tp_qty = 0
            for order in open_orders:
                if order.get("reduceOnly"):
                    qty = float(order.get("origQty", 0))
                    if order["type"] == "STOP_MARKET":
                        sl_qty = qty
                    elif order["type"] == "TAKE_PROFIT_MARKET":
                        tp_qty = qty
            
            # Check if quantities match (1% tolerance)
            sl_match = abs(sl_qty - quantity) / quantity < 0.01 if quantity > 0 else False
            tp_match = abs(tp_qty - quantity) / quantity < 0.01 if quantity > 0 else False
            
            protection_ok = sl_match and tp_match
            
            if not protection_ok:
                logger.info(f"Protection mismatch detected: position={quantity}, SL={sl_qty}, TP={tp_qty}")
                
                # Call update_sl_tp_safe to fix
                try:
                    # Import the result parsing (the tool returns JSON string)
                    result_str = update_sl_tp_safe(symbol, stop_loss_price, take_profit_price)
                    result = json.loads(result_str)
                    
                    if result.get("action") == "updated":
                        actions_taken.append(f"Fixed SL/TP protection: position {quantity}, updated protective orders")
                    elif result.get("action") == "skipped":
                        reason = result.get("reason", "Unknown reason")
                        actions_taken.append(f"SL/TP check: {reason}")
                    else:
                        warnings.append(f"Failed to update SL/TP: {result.get('reason', 'Unknown error')}")
                except Exception as e:
                    warnings.append(f"Exception updating SL/TP: {str(e)}")
            else:
                actions_taken.append("SL/TP protection verified: already optimal")
        
        # ═══════════════════════════════════════
        # Step 3: Clean up orders based on action
        # ═══════════════════════════════════════
        
        # Determine if reversing direction
        is_reversing = (
            has_position and
            (
                (current_direction == "LONG" and new_action == "SHORT") or
                (current_direction == "SHORT" and new_action == "LONG")
            )
        )
        
        if is_reversing:
            # Scenario A: Reversing → need to cancel ALL orders (will close position first)
            try:
                cancelled_count = 0
                for order in open_orders:
                    try:
                        client.cancel_order(symbol, order["orderId"])
                        cancelled_count += 1
                    except:
                        pass
                actions_taken.append(f"Reversing direction: cancelled all {cancelled_count} orders")
            except Exception as e:
                warnings.append(f"Failed to cancel orders during reversal: {str(e)}")
                
        elif has_position:
            # Scenario B: Has position (HOLD/MODIFY) → keep protective orders, cancel entry orders
            try:
                cancelled_count = 0
                kept_count = 0
                for order in open_orders:
                    if order.get("reduceOnly"):
                        # Keep protective orders
                        kept_count += 1
                    else:
                        # Cancel entry orders
                        try:
                            client.cancel_order(symbol, order["orderId"])
                            cancelled_count += 1
                        except:
                            pass
                actions_taken.append(
                    f"Cleaned {cancelled_count} entry orders, kept {kept_count} protective orders"
                )
            except Exception as e:
                warnings.append(f"Failed to clean up orders: {str(e)}")
                
        else:
            # Scenario C: No position → cancel all orders (clean slate)
            try:
                cancelled_count = 0
                for order in open_orders:
                    try:
                        client.cancel_order(symbol, order["orderId"])
                        cancelled_count += 1
                    except:
                        pass
                actions_taken.append(f"No position: cancelled all {cancelled_count} orders")
            except Exception as e:
                warnings.append(f"Failed to cancel orders: {str(e)}")
        
        # ═══════════════════════════════════════
        # Step 4: Return environment status
        # ═══════════════════════════════════════
        
        ready = len(warnings) == 0
        recommendation = "Ready to execute trade" if ready else "Review warnings before proceeding"
        
        # Get account equity
        account_equity = 0
        if has_position and positions:
            account_equity = float(positions[0].get("margin_balance", 0))
        else:
            # Get from account info if no position
            try:
                account_data = client.get_account()
                account_equity = account_data.get("total_wallet_balance", 0) + account_data.get("total_unrealized_profit", 0)
            except:
                pass
        
        return json.dumps({
            "ready": ready,
            "status": {
                "has_position": has_position,
                "position_side": current_direction,
                "position_quantity": abs(position_amt) if has_position else 0,
                "account_equity": account_equity,
                "is_reversing": is_reversing
            },
            "actions_taken": actions_taken,
            "warnings": warnings,
            "recommendation": recommendation
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error preparing trading environment: {str(e)}")
        return json.dumps({
            "ready": False,
            "error": f"Unexpected error: {str(e)}",
            "requires_agent_decision": True
        }, indent=2)
