import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { traders } from "~/features/traders/database/schema";

export const orders = sqliteTable("orders", {
  id: text("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID()),

  // Trader reference
  traderId: text("trader_id")
    .notNull()
    .references(() => traders.id, { onDelete: "cascade" }),

  // External order IDs
  orderId: text("order_id").notNull(), // Exchange order ID
  clientOrderId: text("client_order_id"), // User-defined order ID

  // Trading pair
  symbol: text("symbol").notNull(), // e.g., "BTCUSDT"

  // Order direction and type
  side: text("side", { enum: ["BUY", "SELL"] }).notNull(),
  type: text("type", {
    enum: ["LIMIT", "MARKET", "STOP", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET", "TRAILING_STOP_MARKET"]
  }).notNull(),
  positionSide: text("position_side", { enum: ["BOTH", "LONG", "SHORT"] }).notNull().default("BOTH"),

  // Order status
  status: text("status", {
    enum: ["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]
  }).notNull(),

  // Time in force
  timeInForce: text("time_in_force", {
    enum: ["GTC", "IOC", "FOK", "GTX", "HIDDEN"]
  }),

  // Prices
  price: text("price").notNull().default("0"), // Order price (stored as string for precision)
  avgPrice: text("avg_price").default("0"), // Average fill price
  stopPrice: text("stop_price"), // Stop price for stop orders
  activatePrice: text("activate_price"), // Activation price for trailing stop
  priceRate: text("price_rate"), // Callback rate for trailing stop

  // Quantities
  origQty: text("orig_qty").notNull(), // Original order quantity
  executedQty: text("executed_qty").default("0"), // Executed quantity
  cumQuote: text("cum_quote").default("0"), // Cumulative quote asset traded

  // Order flags
  reduceOnly: integer("reduce_only", { mode: "boolean" }).default(false),
  closePosition: integer("close_position", { mode: "boolean" }).default(false),
  priceProtect: integer("price_protect", { mode: "boolean" }).default(false),

  // Conditional order settings
  workingType: text("working_type", { enum: ["MARK_PRICE", "CONTRACT_PRICE"] }),
  origType: text("orig_type"), // Original order type before trigger

  // Timestamps from exchange
  time: integer("time"), // Order creation time (unix timestamp in ms)
  updateTime: integer("update_time"), // Last update time (unix timestamp in ms)

  // Internal timestamps
  createdAt: text("created_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
  updatedAt: text("updated_at")
    .notNull()
    .$defaultFn(() => new Date().toISOString()),
});

// Zod validation schemas
export const insertOrderSchema = createInsertSchema(orders, {
  symbol: () => z.string().min(1, "Symbol is required"),
  side: () => z.enum(["BUY", "SELL"]),
  type: () => z.enum(["LIMIT", "MARKET", "STOP", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET", "TRAILING_STOP_MARKET"]),
  status: () => z.enum(["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]),
  positionSide: () => z.enum(["BOTH", "LONG", "SHORT"]),
  timeInForce: () => z.enum(["GTC", "IOC", "FOK", "GTX", "HIDDEN"]).optional(),
  orderId: () => z.string().min(1, "Order ID is required"),
  origQty: () => z.string().min(1, "Quantity is required"),
  price: () => z.string(),
  workingType: () => z.enum(["MARK_PRICE", "CONTRACT_PRICE"]).optional(),
  clientOrderId: () => z.string().nullish().transform(val => val ?? undefined),
  createdAt: () => z.string().datetime().optional(),
  updatedAt: () => z.string().datetime().optional(),
});

export const selectOrderSchema = createSelectSchema(orders);

// Query parameter schemas
export const getOrdersQuerySchema = z.object({
  traderId: z.string().optional(),
  symbol: z.string().optional(),
  side: z.enum(["BUY", "SELL"]).optional(),
  status: z.enum(["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]).optional(),
  startTime: z.number().optional(),
  endTime: z.number().optional(),
  limit: z.number().min(1).max(1000).default(500),
  offset: z.number().min(0).default(0),
});

export type GetOrdersQuery = z.infer<typeof getOrdersQuerySchema>;
