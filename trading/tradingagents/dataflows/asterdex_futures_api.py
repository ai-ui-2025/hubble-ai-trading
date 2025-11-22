"""
Aster Futures API Client
Wrapper for Aster Futures REST API v3

Reference: https://github.com/asterdex/api-docs/blob/master/aster-finance-futures-api-v3_CN.md
"""

import hmac
import hashlib
import time
import random
import requests
from typing import Dict, List, Optional, Union
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
import os
from loguru import logger


class AsterFuturesClient:
    """Aster Futures REST API Client"""
    
    def __init__(
        self, 
        api_key: str, 
        api_secret: str, 
        base_url: str = "https://fapi.asterdex.com",
        max_retries: int = 5,
        retry_delay: float = 1.0,
        timeout: float = 5.0
    ):
        """
        Initialize Aster Futures client
        
        Args:
            api_key: API key (required)
            api_secret: API secret (required)
            base_url: API base URL (default: https://fapi.asterdex.com)
            max_retries: Maximum number of retry attempts for 429 errors (default: 5)
            retry_delay: Base delay in seconds for exponential backoff (default: 1.0)
            timeout: Request timeout in seconds (default: 30.0)
        """
        if not api_key:
            raise ValueError("api_key is required")
        if not api_secret:
            raise ValueError("api_secret is required")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-MBX-APIKEY": self.api_key  # Use the Binance-standard header name
        })
        
        # Local cache
        self._symbol_filters = {}
        self._leverage_brackets = {}
        self._last_sync_time = 0
        
    def _generate_signature(self, params: Dict) -> str:
        """
        Generate request signature
        
        Args:
            params: Request parameters
            
        Returns:
            Signature string
        """
        # ⚠️ CRITICAL: Aster DEX does NOT require sorted parameters!
        # Unlike standard Binance API, Asterdex uses insertion order
        # Tested and confirmed: sorting causes signature validation to fail
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _sync_server_time(self):
        """Sync server time to avoid clock offset"""
        try:
            response = self.session.get(f"{self.base_url}/fapi/v1/time", timeout=self.timeout)
            if response.status_code == 200:
                server_time = response.json()['serverTime']
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
                self._last_sync_time = time.time()
        except Exception as e:
            logger.warning(f"Clock sync failed: {e}")
            self.time_offset = 0
    
    def _get_timestamp(self) -> int:
        """
        Get server timestamp (with clock offset)
        
        Returns:
            Timestamp in milliseconds
        """
        # Re-sync every hour
        if time.time() - self._last_sync_time > 3600:
            self._sync_server_time()
        
        return int(time.time() * 1000) + getattr(self, 'time_offset', 0)
    
    def _request(self, method: str, endpoint: str, signed: bool = False, **kwargs) -> Dict:
        """
        Generic request method with retry logic for rate limits
        
        Args:
            method: HTTP method (GET/POST/DELETE)
            endpoint: API endpoint
            signed: Whether signature is required
            **kwargs: Additional parameters
            
        Returns:
            Response data
            
        Raises:
            requests.exceptions.HTTPError: For non-retryable HTTP errors
            Exception: For other request exceptions
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries + 1):
            # Refresh signature for each attempt if signed request
            if signed:
                params = kwargs.get('params', {})
                # Remove old signature if retrying
                if 'signature' in params:
                    del params['signature']
                params['timestamp'] = self._get_timestamp()
                params['recvWindow'] = 5000
                params['signature'] = self._generate_signature(params)
                kwargs['params'] = params
            
            try:
                # Add timeout to prevent indefinite waiting
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = self.timeout
                
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                response = e.response
                
                # Handle 429 rate limit errors
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        # Calculate retry delay
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                # If Retry-After is not a number, use exponential backoff
                                delay = self.retry_delay * (2 ** attempt)
                        else:
                            # Exponential backoff with jitter
                            delay = self.retry_delay * (2 ** attempt)
                        
                        # Add jitter (±20% random variation)
                        jitter = delay * 0.2 * (2 * random.random() - 1)
                        delay = delay + jitter
                        
                        logger.warning(
                            f"⚠️ Rate limit hit (429) on {method} {endpoint}. "
                            f"Retry {attempt + 1}/{self.max_retries} after {delay:.2f}s"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"❌ Rate limit exceeded after {self.max_retries} retries on {method} {endpoint}"
                        )
                        logger.error(f"Response: {response.text}")
                        raise
                
                # For non-429 errors, log and raise immediately
                logger.error(f"API request failed: {e}")
                logger.error(f"Response: {response.text}")
                raise
                
            except requests.exceptions.Timeout as e:
                # Handle timeout errors
                logger.error(f"Request timeout after {self.timeout}s: {method} {endpoint}")
                raise Exception(f"API request timeout after {self.timeout}s") from e
                
            except requests.exceptions.ConnectionError as e:
                # Handle connection errors
                logger.error(f"Connection error: {method} {endpoint} - {e}")
                raise Exception(f"API connection failed: {e}") from e
                
            except Exception as e:
                # For other non-HTTP errors (network issues, etc.), do not retry
                logger.error(f"Request exception: {method} {endpoint} - {e}")
                raise
        
        # This should never be reached, but just in case
        raise Exception(f"Unexpected: exhausted all retry attempts for {method} {endpoint}")
    
    # ==================== Market data endpoints ====================
    
    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> List[Dict]:
        """
        Fetch candlestick (kline) data.
        
        Args:
            symbol: Trading pair, e.g., "BTCUSDT".
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d).
            limit: Number of klines to return.
            
        Returns:
            A list of kline dictionaries.
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        data = self._request("GET", "/fapi/v1/klines", params=params)
        
        # Convert to a friendlier structure
        klines = []
        for k in data:
            klines.append({
                "open_time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": k[6],
                "quote_volume": float(k[7]),
                "trades": int(k[8]),
            })
        
        return klines
    
    def get_mark_price(self, symbol: str) -> Dict:
        """
        Fetch mark price information.
        
        Args:
            symbol: Trading pair.
        
        Returns:
            Mark price payload (includes mark price, index price, funding rate).
        """
        params = {"symbol": symbol}
        data = self._request("GET", "/fapi/v1/premiumIndex", params=params)
        
        return {
            "symbol": data["symbol"],
            "mark_price": float(data["markPrice"]),
            "index_price": float(data["indexPrice"]),
            "funding_rate": float(data["lastFundingRate"]),
            "next_funding_time": data["nextFundingTime"],
        }
    
    def get_funding_rate_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """
        Fetch historical funding rates.
        
        Args:
            symbol: Trading pair.
            limit: Number of entries to fetch.
            
        Returns:
            Funding rate history.
        """
        params = {
            "symbol": symbol,
            "limit": limit
        }
        return self._request("GET", "/fapi/v1/fundingRate", params=params)
    
    def get_open_interest(self, symbol: str) -> Dict:
        """
        Fetch open interest statistics.
        
        Args:
            symbol: Trading pair.
            
        Returns:
            Open interest payload.
        """
        params = {"symbol": symbol}
        data = self._request("GET", "/fapi/v1/openInterest", params=params)
        
        return {
            "symbol": data["symbol"],
            "open_interest": float(data["openInterest"]),
            "timestamp": data["time"]
        }
    
    def get_ticker_24hr(self, symbol: str) -> Dict:
        """
        Fetch 24-hour price change statistics.
        
        Args:
            symbol: Trading pair.
            
        Returns:
            24-hour ticker statistics.
        """
        params = {"symbol": symbol}
        return self._request("GET", "/fapi/v1/ticker/24hr", params=params)
    
    def get_depth(self, symbol: str, limit: int = 20) -> Dict:
        """
        Fetch orderbook depth.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            limit: Depth limit (default: 20, valid: [5, 10, 20, 50, 100, 500, 1000])
            
        Returns:
            Orderbook data with bids and asks
            {
                "lastUpdateId": int,
                "bids": [[price, quantity], ...],
                "asks": [[price, quantity], ...]
            }
        """
        params = {"symbol": symbol, "limit": limit}
        return self._request("GET", "/fapi/v1/depth", params=params)
    
    # ==================== Exchange metadata endpoints ====================
    
    def get_exchange_info(self) -> Dict:
        """
        Fetch exchange information (contract specs, filters, etc.).
        
        Returns:
            Exchange metadata.
        """
        return self._request("GET", "/fapi/v1/exchangeInfo")
    
    def get_symbol_filters(self, symbol: str, force_refresh: bool = False) -> Dict:
        """
        Fetch symbol filters (price precision, quantity precision, min notional, etc.).
        
        This fetches futures contract-specific trading rules from /fapi/v1/exchangeInfo.
        According to Aster DEX Futures API docs, futures use 'NOTIONAL' filter (not 'MIN_NOTIONAL').
        
        Args:
            symbol: Trading pair.
            force_refresh: Whether to bypass the cache and fetch fresh data from API.
            
        Returns:
            Filter information including futures contract specs.
        """
        if symbol in self._symbol_filters and not force_refresh:
            return self._symbol_filters[symbol]
        
        exchange_info = self.get_exchange_info()
        
        
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                filters = {}
                
                # Contract specifications (futures-specific)
                filters['contract_type'] = s.get('contractType', '')
                filters['contract_size'] = float(s.get('contractSize', 1.0))
                filters['contract_status'] = s.get('contractStatus', '')
                filters['underlying_type'] = s.get('underlyingType', '')
                
                # Precision settings
                filters['price_precision'] = int(s.get('pricePrecision', 0))
                filters['quantity_precision'] = int(s.get('quantityPrecision', 0))
                filters['base_asset_precision'] = int(s.get('baseAssetPrecision', 0))
                filters['quote_precision'] = int(s.get('quotePrecision', 0))
                
                # Extract filter rules
                # Note: Futures API uses 'NOTIONAL' filter (not 'MIN_NOTIONAL' like spot)
                # Process NOTIONAL first (futures standard), then MIN_NOTIONAL as fallback
                for f in s['filters']:
                    filter_type = f['filterType']
                    
                    if filter_type == 'PRICE_FILTER':
                        filters['tick_size'] = float(f['tickSize'])
                        filters['min_price'] = float(f['minPrice'])
                        filters['max_price'] = float(f['maxPrice'])
                    elif filter_type == 'LOT_SIZE':
                        filters['step_size'] = float(f['stepSize'])
                        filters['min_qty'] = float(f['minQty'])
                        filters['max_qty'] = float(f['maxQty'])
                    elif filter_type == 'NOTIONAL':
                        # Futures API standard: Aster DEX uses 'minNotional' field (Binance-compatible)
                        # Try multiple possible field names
                        min_notional_val = (
                            f.get('minNotional') or 
                            f.get('minNotionalValue') or
                            f.get('notional') or 
                            f.get('notionalValue')
                        )
                        if min_notional_val:
                            filters['min_notional'] = float(min_notional_val)
                        else:
                            # Log warning if NOTIONAL filter exists but no minNotional found
                            logger.warning(f"NOTIONAL filter found for {symbol} but no minNotional field. Filter keys: {list(f.keys())}")
                        
                        max_notional_val = f.get('maxNotional') or f.get('maxNotionalValue')
                        if max_notional_val:
                            filters['max_notional'] = float(max_notional_val)
                    elif filter_type == 'MIN_NOTIONAL':
                        # Spot API format - only use if NOTIONAL not found
                        if 'min_notional' not in filters:
                            filters['min_notional'] = float(f.get('notional', f.get('notionalValue', 0)))
                    elif filter_type == 'MAX_NUM_ORDERS':
                        filters['max_num_orders'] = int(f.get('maxNumOrders', 0))
                    elif filter_type == 'MAX_NUM_ALGO_ORDERS':
                        filters['max_num_algo_orders'] = int(f.get('maxNumAlgoOrders', 0))
                    elif filter_type == 'PERCENT_PRICE':
                        filters['multiplier_up'] = float(f.get('multiplierUp', 0))
                        filters['multiplier_down'] = float(f.get('multiplierDown', 0))
                        filters['multiplier_decimal'] = float(f.get('multiplierDecimal', 0))
                    else:
                        # Log unknown filter types for debugging
                        logger.debug(f"Unknown filter type for {symbol}: {filter_type} = {f}")
                
                self._symbol_filters[symbol] = filters
                return filters
        
        raise ValueError(f"Symbol {symbol} not found")
    
    def get_leverage_bracket(self, symbol: str = None, force_refresh: bool = False) -> Dict:
        """
        Fetch leverage bracket information (maintenance margin rates by leverage).
        
        This is futures-specific information that shows margin requirements at different leverage levels.
        
        Args:
            symbol: Optional trading pair. If None, returns all symbols.
            force_refresh: Whether to bypass the cache.
            
        Returns:
            Leverage bracket information.
        """
        cache_key = symbol or 'ALL'
        
        if cache_key in self._leverage_brackets and not force_refresh:
            return self._leverage_brackets[cache_key]
        
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        # Try the leverage bracket endpoint (Binance-compatible)
        try:
            data = self._request("GET", "/fapi/v1/leverageBracket", params=params)
            self._leverage_brackets[cache_key] = data
            return data
        except Exception as e:
            # If endpoint doesn't exist, return empty structure
            logger.debug(f"Leverage bracket endpoint not available: {e}")
            return []

    def _format_decimal(
        self,
        value: float,
        step: Optional[float] = None,
        precision: Optional[int] = None,
        rounding=ROUND_DOWN
    ) -> str:
        """
        Format numeric values so they comply with exchange precision rules.
        """
        if value is None:
            return None
        decimal_value = Decimal(str(value))

        if step:
            step_decimal = Decimal(str(step))
            if step_decimal > 0:
                multiple = (decimal_value / step_decimal).to_integral_value(rounding=rounding)
                decimal_value = (multiple * step_decimal).quantize(step_decimal, rounding=rounding)

        if precision is not None and precision >= 0:
            quant = Decimal('1').scaleb(-precision)
            decimal_value = decimal_value.quantize(quant, rounding=rounding)

        normalized = decimal_value.normalize()
        # Ensure plain string representation (no scientific notation)
        return format(normalized, 'f')
    
    # ==================== Account and position endpoints ====================
    
    def get_account(self) -> Dict:
        """
        Fetch account information.
        
        Returns:
            Account balances and margin metrics.
        """
        data = self._request("GET", "/fapi/v2/account", signed=True)
        
        return {
            "total_wallet_balance": float(data["totalWalletBalance"]),
            "total_unrealized_profit": float(data["totalUnrealizedProfit"]),
            "total_margin_balance": float(data["totalMarginBalance"]),
            "total_position_initial_margin": float(data["totalPositionInitialMargin"]),
            "total_open_order_initial_margin": float(data["totalOpenOrderInitialMargin"]),
            "available_balance": float(data["availableBalance"]),
            "max_withdraw_amount": float(data["maxWithdrawAmount"]),
            "assets": data.get("assets", []),
            "positions": data.get("positions", [])
        }
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """
        Fetch current positions.
        
        Args:
            symbol: Optional trading pair filter.
            
        Returns:
            A list of open positions.
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        data = self._request("GET", "/fapi/v2/positionRisk", signed=True, params=params)
        
        positions = []
        for p in data:
            # Only include positions with non-zero size
            if float(p['positionAmt']) != 0:
                positions.append({
                    "symbol": p["symbol"],
                    "position_amt": float(p["positionAmt"]),
                    "entry_price": float(p["entryPrice"]),
                    "mark_price": float(p["markPrice"]),
                    "unrealized_profit": float(p["unRealizedProfit"]),
                    "liquidation_price": float(p["liquidationPrice"]),
                    "leverage": int(p["leverage"]),
                    "margin_type": p["marginType"],
                    "isolated_margin": float(p.get("isolatedMargin", 0)),
                    "position_side": p.get("positionSide", "BOTH")
                })
        
        return positions
    
    def get_balance(self) -> Dict:
        """
        Fetch account balance summary.
        
        Returns:
            Balance information.
        """
        account = self.get_account()
        return {
            "available_balance": account["available_balance"],
            "total_margin_balance": account["total_margin_balance"],
            "total_unrealized_profit": account["total_unrealized_profit"]
        }
    
    # ==================== Trading endpoints ====================
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        Configure leverage for a symbol.
        
        Args:
            symbol: Trading pair.
            leverage: Leverage value (1-125).
            
        Returns:
            API response.
        """
        params = {
            "symbol": symbol,
            "leverage": leverage
        }
        return self._request("POST", "/fapi/v1/leverage", signed=True, params=params)
    
    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> Dict:
        """
        Configure margin mode.
        
        Args:
            symbol: Trading pair.
            margin_type: Margin mode ("ISOLATED" or "CROSSED").
            
        Returns:
            API response.
        """
        params = {
            "symbol": symbol,
            "marginType": margin_type
        }
        return self._request("POST", "/fapi/v1/marginType", signed=True, params=params)
    
    def place_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        order_type: str = "LIMIT",  # "LIMIT", "MARKET", "STOP", "TAKE_PROFIT"
        quantity: float = None,
        price: float = None,
        stop_price: float = None,
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        client_order_id: str = None,
        **kwargs
    ) -> Dict:
        """
        Place an order.
        
        Args:
            symbol: Trading pair.
            side: Direction ("BUY" opens long/closes short, "SELL" opens short/closes long).
            order_type: Order type.
            quantity: Order quantity.
            price: Price (required for limit orders).
            stop_price: Trigger price (required for stop orders).
            reduce_only: Reduce-only flag.
            time_in_force: Time-in-force ("GTC", "IOC", "FOK").
            client_order_id: Optional client order id (for idempotency).
            
        Returns:
            Order information.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
        }

        filters = None
        
        if quantity is not None:
            filters = filters or self.get_symbol_filters(symbol)
            params["quantity"] = self._format_decimal(
                quantity,
                step=filters.get("step_size"),
                precision=filters.get("quantity_precision"),
                rounding=ROUND_DOWN
            )
        if price is not None:
            filters = filters or self.get_symbol_filters(symbol)
            params["price"] = self._format_decimal(
                price,
                step=filters.get("tick_size"),
                precision=filters.get("price_precision"),
                rounding=ROUND_HALF_UP
            )
        if stop_price is not None:
            filters = filters or self.get_symbol_filters(symbol)
            params["stopPrice"] = self._format_decimal(
                stop_price,
                step=filters.get("tick_size"),
                precision=filters.get("price_precision"),
                rounding=ROUND_HALF_UP
            )
        if reduce_only:
            params["reduceOnly"] = "true"
        if time_in_force and order_type == "LIMIT":
            params["timeInForce"] = time_in_force
        if client_order_id:
            params["newClientOrderId"] = client_order_id
        
        # Append any additional parameters passed via kwargs
        params.update(kwargs)
        
        return self._request("POST", "/fapi/v1/order", signed=True, params=params)
    
    def cancel_order(self, symbol: str, order_id: int = None, client_order_id: str = None) -> Dict:
        """
        Cancel a specific order.
        
        Args:
            symbol: Trading pair.
            order_id: Order identifier.
            client_order_id: Client order identifier.
            
        Returns:
            Cancellation result.
        """
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise ValueError("Must provide either order_id or client_order_id")
        
        return self._request("DELETE", "/fapi/v1/order", signed=True, params=params)
    
    def get_order(self, symbol: str, order_id: int = None, client_order_id: str = None) -> Dict:
        """
        Query an order.
        
        Args:
            symbol: Trading pair.
            order_id: Order identifier.
            client_order_id: Client order identifier.
            
        Returns:
            Order information.
        """
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise ValueError("Must provide either order_id or client_order_id")
        
        return self._request("GET", "/fapi/v1/order", signed=True, params=params)
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        Fetch open orders.
        
        Args:
            symbol: Optional trading pair filter.
            
        Returns:
            List of open orders.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return self._request("GET", "/fapi/v1/openOrders", signed=True, params=params)
    
    def cancel_all_orders(self, symbol: str) -> Dict:
        """
        Cancel all open orders for the symbol.
        
        Args:
            symbol: Trading pair.
            
        Returns:
            Cancellation result.
        """
        params = {"symbol": symbol}
        return self._request("DELETE", "/fapi/v1/allOpenOrders", signed=True, params=params)
    
    # ==================== Advanced trading helpers ====================
    
    def place_sl_tp_orders(
        self,
        symbol: str,
        side: str,  # "BUY" to close long or "SELL" to close short
        quantity: float,
        stop_loss_price: float = None,
        take_profit_price: float = None,
        trigger_type: str = "MARK_PRICE"  # "MARK_PRICE", "CONTRACT_PRICE", "INDEX_PRICE"
    ) -> Dict:
        """
        Submit stop-loss and take-profit orders using mark price triggers.
        
        Args:
            symbol: Trading pair.
            side: Close direction ("SELL" to close long, "BUY" to close short).
            quantity: Position quantity to protect.
            stop_loss_price: Stop-loss price.
            take_profit_price: Take-profit price.
            trigger_type: Price type used for triggering.
            
        Returns:
            Order placement details.
        """
        filters = self.get_symbol_filters(symbol)
        tick_size = filters.get("tick_size")
        tick_decimal = Decimal(str(tick_size)) if tick_size else None

        def _align_price(price: Optional[float]) -> Optional[float]:
            if price is None or tick_decimal is None or tick_decimal <= 0:
                return price
            return float(Decimal(str(price)).quantize(tick_decimal, rounding=ROUND_HALF_UP))

        stop_loss_price = _align_price(stop_loss_price)
        take_profit_price = _align_price(take_profit_price)

        result = {"stop_loss": None, "take_profit": None}
        
        # Place stop-loss order when requested
        if stop_loss_price:
            sl_order = self.place_order(
                symbol=symbol,
                side=side,
                order_type="STOP_MARKET",
                quantity=quantity,
                stop_price=stop_loss_price,
                reduce_only=True,
                workingType=trigger_type
            )
            result["stop_loss"] = sl_order
        
        # Place take-profit order when requested
        if take_profit_price:
            tp_order = self.place_order(
                symbol=symbol,
                side=side,
                order_type="TAKE_PROFIT_MARKET",
                quantity=quantity,
                stop_price=take_profit_price,
                reduce_only=True,
                workingType=trigger_type
            )
            result["take_profit"] = tp_order
        
        return result
    
    def close_position(self, symbol: str, percent: float = 100.0) -> Dict:
        """
        Close an existing position by percentage.
        
        Args:
            symbol: Trading pair.
            percent: Percentage of the position to close (0-100).
            
        Returns:
            Close-order result.
        """
        positions = self.get_positions(symbol)
        
        if not positions:
            return {"message": "No position to close"}
        
        position = positions[0]
        position_amt = position["position_amt"]
        
        # Determine the quantity to close
        close_qty = abs(position_amt) * (percent / 100.0)
        
        # Determine the closing direction
        side = "SELL" if position_amt > 0 else "BUY"
        
        # Execute a market order to close the position
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=close_qty,
            reduce_only=True
        )
    
    # ==================== Helper methods ====================
    
    def validate_order_params(self, symbol: str, price: float, quantity: float) -> Dict:
        """
        Validate order parameters against exchange filters.
        
        Args:
            symbol: Trading pair.
            price: Proposed order price.
            quantity: Proposed order quantity.
            
        Returns:
            Validation result and adjusted parameters.
        """
        filters = self.get_symbol_filters(symbol)
        
        # Validate and adjust price
        tick_size = filters['tick_size']
        adjusted_price = round(price / tick_size) * tick_size
        
        # Validate and adjust quantity
        step_size = filters['step_size']
        adjusted_quantity = round(quantity / step_size) * step_size
        
        # Validate minimum notional
        notional = adjusted_price * adjusted_quantity
        min_notional = filters.get('min_notional', 0)
        
        validation = {
            "valid": True,
            "adjusted_price": adjusted_price,
            "adjusted_quantity": adjusted_quantity,
            "notional": notional,
            "errors": []
        }
        
        if adjusted_price < filters['min_price']:
            validation["valid"] = False
            validation["errors"].append(f"Price {adjusted_price} below minimum {filters['min_price']}")
        
        if adjusted_quantity < filters['min_qty']:
            validation["valid"] = False
            validation["errors"].append(f"Quantity {adjusted_quantity} below minimum {filters['min_qty']}")
        
        if notional < min_notional:
            validation["valid"] = False
            validation["errors"].append(f"Notional {notional} below minimum {min_notional}")
        
        return validation
    
    def calculate_liquidation_price(
        self,
        entry_price: float,
        leverage: int,
        side: str,  # "LONG" or "SHORT"
        maintenance_margin_rate: float = 0.005  # Maintenance margin rate, default 0.5%
    ) -> float:
        """
        Calculate an approximate liquidation price.
        
        Args:
            entry_price: Entry price.
            leverage: Leverage value.
            side: Position side.
            maintenance_margin_rate: Maintenance margin rate.
            
        Returns:
            Estimated liquidation price.
        """
        if side == "LONG":
            liq_price = entry_price * (1 - (1 / leverage) + maintenance_margin_rate)
        else:  # SHORT
            liq_price = entry_price * (1 + (1 / leverage) - maintenance_margin_rate)
        
        return liq_price
