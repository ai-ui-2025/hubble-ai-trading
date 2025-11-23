/**
 * Order feature - Trading order management
 *
 * This feature manages trading orders for traders, including:
 * - Order creation and tracking
 * - Support for various order types (LIMIT, MARKET, STOP, etc.)
 * - Order status management (NEW, FILLED, CANCELED, etc.)
 * - Historical order queries with filtering
 * - Batch import from exchange APIs
 */

// Re-export client-safe types
export type {
  Order,
  OrderSide,
  OrderType,
  PositionSide,
  OrderStatus,
  TimeInForce,
  WorkingType,
  GetOrdersParams,
  GetOrdersResponse,
  CreateOrderInput,
  UpdateOrderInput,
  ImportOrdersInput,
  ImportOrdersResponse,
} from "./database/types";

// Re-export validation schemas (client-safe)
export { getOrdersQuerySchema } from "./database/schema";

// Hooks (client-safe)
export {
  useLatestOrders,
  orderKeys,
  type LatestOrdersResponse,
} from "./hooks/use-latest-orders";
