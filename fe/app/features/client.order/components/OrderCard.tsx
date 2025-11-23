import type { Order, OrderType, OrderStatus } from "~/features/order";
import { getTraderBackgroundColor } from "~/features/client.chart/utils/trader-color";

interface OrderCardProps {
  order: Order & {
    traderName?: string | null;
  };
  allTraderIds?: string[];
}

/**
 * Format timestamp to readable date-time string
 */
function formatTimestamp(timestamp: number | null): string {
  if (!timestamp) return "N/A";
  return new Date(timestamp).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Get order type display name
 */
function getOrderTypeDisplay(type: OrderType): string {
  const typeMap: Record<OrderType, string> = {
    LIMIT: "Limit",
    MARKET: "Market",
    STOP: "Stop Limit",
    STOP_MARKET: "Stop Market",
    TAKE_PROFIT: "Take Profit Limit",
    TAKE_PROFIT_MARKET: "Take Profit Market",
    TRAILING_STOP_MARKET: "Trailing Stop",
  };
  return typeMap[type] || type;
}

/**
 * Check if order is a conditional order (stop/take profit orders)
 */
function isConditionalOrder(type: OrderType): boolean {
  return (
    type === "STOP" ||
    type === "STOP_MARKET" ||
    type === "TAKE_PROFIT" ||
    type === "TAKE_PROFIT_MARKET" ||
    type === "TRAILING_STOP_MARKET"
  );
}

/**
 * Check if order is waiting (conditional order waiting to trigger)
 * Only NEW status conditional orders are considered as waiting
 */
function isOrderWaiting(type: OrderType, status: OrderStatus): boolean {
  return isConditionalOrder(type) && status === "NEW";
}

/**
 * Get order status display name
 */
function getOrderStatusDisplay(status: OrderStatus): string {
  const statusMap: Record<OrderStatus, string> = {
    NEW: "New",
    PARTIALLY_FILLED: "Partial",
    FILLED: "Filled",
    CANCELED: "Canceled",
    REJECTED: "Rejected",
    EXPIRED: "Expired",
  };
  return statusMap[status] || status;
}

/**
 * Get order status color class
 */
function getOrderStatusColor(
  type: OrderType,
  status: OrderStatus
): string {
  if (status === "FILLED") {
    return "bg-chart-1 text-primary-foreground"; // Green
  }
  if (status === "PARTIALLY_FILLED") {
    return "bg-chart-4 text-primary-foreground"; // Yellow/Orange
  }
  if (isOrderWaiting(type, status)) {
    // Conditional order waiting to trigger - use orange to indicate waiting
    return "bg-chart-4 text-primary-foreground"; // Orange
  }
  if (status === "CANCELED" || status === "EXPIRED" || status === "REJECTED") {
    return "bg-muted text-muted-foreground"; // Gray
  }
  // NEW status for non-conditional orders
  return "bg-chart-3 text-primary-foreground"; // Blue
}

/**
 * Get side display (BUY/SELL)
 */
function getSideDisplay(side: Order["side"]): string {
  return side;
}

/**
 * Get side color
 */
function getSideColor(side: Order["side"]): string {
  return side === "BUY" ? "text-chart-1" : "text-destructive";
}

/**
 * Order card component
 * Displays:
 * 1. Trader name (small)
 * 2. Symbol
 * 3. Order type
 * 4. Order status (filled/waiting, conditional orders have special styling when waiting)
 * 5. Side (BUY/SELL)
 * 6. Price
 * 7. Quantity
 * 8. Time
 */
export function OrderCard({ order, allTraderIds }: OrderCardProps) {
  const traderBgColor =
    order.traderId && order.traderName
      ? getTraderBackgroundColor(
          order.traderId,
          allTraderIds,
          order.traderName,
          "",
          1
        )
      : undefined;

  const isWaiting = isOrderWaiting(order.type, order.status);
  const orderTypeDisplay = getOrderTypeDisplay(order.type);
  const orderStatusDisplay = getOrderStatusDisplay(order.status);
  const sideDisplay = getSideDisplay(order.side);

  return (
    <div
      className={`p-3 bg-card/20 border-b border-primary/10 last:border-b-0 transition-all duration-300 hover:bg-primary/5 group relative ${
        isWaiting ? "bg-chart-4/10" : ""
      }`}
    >
      {/* Hover glow effect */}
      <div className="absolute left-0 top-0 bottom-0 w-[2px] transition-all duration-300 group-hover:h-full group-hover:bg-primary bg-transparent" />
      
      {/* Compact header row: Trader + Symbol */}
      <div className="flex items-center gap-2 mb-2">
        {/* Trader name - small */}
        {order.traderName && (
          <span
            className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-white shadow-sm font-mono"
            style={{
              backgroundColor: traderBgColor,
            }}
          >
            {order.traderName}
          </span>
        )}

        {/* Symbol - prominent */}
        <span className="font-black text-xs text-foreground flex-1 tracking-wide group-hover:text-primary transition-colors">
          {order.symbol}
        </span>

        {/* Side badge - BUY/SELL */}
        <span
          className={`px-1.5 py-0.5 text-[9px] font-black font-mono tracking-wider ${getSideColor(order.side)}`}
        >
          {sideDisplay}
        </span>
      </div>

      {/* Info grid - compact 2 column layout */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
        {/* Order Type */}
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground/70 uppercase tracking-wider text-[9px]">Type</span>
          <span className="font-semibold text-foreground">{orderTypeDisplay}</span>
        </div>

        {/* Order Status */}
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground/70 uppercase tracking-wider text-[9px]">Status</span>
          <span
            className={`px-1.5 py-[1px] text-[9px] font-bold uppercase tracking-wider ${getOrderStatusColor(order.type, order.status)}`}
          >
            {orderStatusDisplay}
          </span>
        </div>

        {/* Price */}
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground/70 uppercase tracking-wider text-[9px]">Price</span>
          <span className="font-bold text-foreground">
            {parseFloat(order.price) === 0
              ? "MKT"
              : parseFloat(order.price).toLocaleString()}
          </span>
        </div>

        {/* Quantity */}
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground/70 uppercase tracking-wider text-[9px]">Qty</span>
          <span className="font-bold text-foreground">{order.origQty}</span>
        </div>

        {/* Time - full width */}
        <div className="col-span-2 flex items-center justify-between pt-2 mt-1 border-t border-dashed border-primary/20">
          <span className="text-muted-foreground/50 uppercase tracking-widest text-[8px]">Time</span>
          <span className="font-medium text-muted-foreground text-[9px]">
            {formatTimestamp(order.time)}
          </span>
        </div>
      </div>
    </div>
  );
}
