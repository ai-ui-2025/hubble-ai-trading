import { z } from "zod";

// Order side
export type OrderSide = "BUY" | "SELL";

// Order type
export type OrderType =
  | "LIMIT"
  | "MARKET"
  | "STOP"
  | "STOP_MARKET"
  | "TAKE_PROFIT"
  | "TAKE_PROFIT_MARKET"
  | "TRAILING_STOP_MARKET";

// Position side
export type PositionSide = "BOTH" | "LONG" | "SHORT";

// Order status
export type OrderStatus =
  | "NEW"
  | "PARTIALLY_FILLED"
  | "FILLED"
  | "CANCELED"
  | "REJECTED"
  | "EXPIRED";

// Time in force
export type TimeInForce = "GTC" | "IOC" | "FOK" | "GTX" | "HIDDEN";

// Working type for conditional orders
export type WorkingType = "MARK_PRICE" | "CONTRACT_PRICE";

// Order record type (matching database schema)
export interface Order {
  id: string;
  traderId: string;
  orderId: string;
  clientOrderId: string | null;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  positionSide: PositionSide;
  status: OrderStatus;
  timeInForce: TimeInForce | null;
  price: string;
  avgPrice: string | null;
  stopPrice: string | null;
  activatePrice: string | null;
  priceRate: string | null;
  origQty: string;
  executedQty: string | null;
  cumQuote: string | null;
  reduceOnly: boolean | null;
  closePosition: boolean | null;
  priceProtect: boolean | null;
  workingType: WorkingType | null;
  origType: string | null;
  time: number | null;
  updateTime: number | null;
  createdAt: string;
  updatedAt: string;
}

// Query parameters for fetching orders
export interface GetOrdersParams {
  traderId?: string;
  symbol?: string;
  side?: OrderSide;
  status?: OrderStatus;
  startTime?: number;
  endTime?: number;
  limit?: number;
  offset?: number;
}

// API response types
export interface GetOrdersResponse {
  orders: Order[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateOrderInput {
  traderId: string;
  orderId: string;
  clientOrderId?: string;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  positionSide?: PositionSide;
  status: OrderStatus;
  timeInForce?: TimeInForce;
  price?: string;
  avgPrice?: string;
  stopPrice?: string;
  activatePrice?: string;
  priceRate?: string;
  origQty: string;
  executedQty?: string;
  cumQuote?: string;
  reduceOnly?: boolean;
  closePosition?: boolean;
  priceProtect?: boolean;
  workingType?: WorkingType;
  origType?: string;
  time?: number;
  updateTime?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface UpdateOrderInput {
  status?: OrderStatus;
  executedQty?: string;
  avgPrice?: string;
  cumQuote?: string;
  updateTime?: number;
}

// Batch import from exchange API
export interface ImportOrdersInput {
  traderId: string;
  orders: CreateOrderInput[];
}

export interface ImportOrdersResponse {
  imported: number;
  skipped: number;
  errors: string[];
}
