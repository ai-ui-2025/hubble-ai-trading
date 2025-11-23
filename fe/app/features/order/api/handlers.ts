import type { DrizzleD1Database } from "drizzle-orm/d1";
import type * as schema from "@/schema";
import { orders } from "../database/schema";
import { eq, and, desc, gte, lte, count, sql } from "drizzle-orm";
import type {
  CreateOrderInput,
  UpdateOrderInput,
  GetOrdersParams,
  GetOrdersResponse,
  ImportOrdersInput,
  ImportOrdersResponse,
} from "../database/types";
import { traders } from "@/schema";

/**
 * Create a single order record
 */
export async function createOrder(
  db: DrizzleD1Database<typeof schema>,
  data: CreateOrderInput
) {
  const [order] = await db
    .insert(orders)
    .values({
      traderId: data.traderId,
      orderId: data.orderId,
      clientOrderId: data.clientOrderId,
      symbol: data.symbol,
      side: data.side,
      type: data.type,
      positionSide: data.positionSide || "BOTH",
      status: data.status,
      timeInForce: data.timeInForce,
      price: data.price || "0",
      avgPrice: data.avgPrice,
      stopPrice: data.stopPrice,
      activatePrice: data.activatePrice,
      priceRate: data.priceRate,
      origQty: data.origQty,
      executedQty: data.executedQty,
      cumQuote: data.cumQuote,
      reduceOnly: data.reduceOnly || false,
      closePosition: data.closePosition || false,
      priceProtect: data.priceProtect || false,
      workingType: data.workingType,
      origType: data.origType,
      time: data.time,
      updateTime: data.updateTime,
      createdAt: data.createdAt ?? new Date().toISOString(),
      updatedAt: data.updatedAt ?? new Date().toISOString(),
    })
    .returning();

  return order;
}

/**
 * Get orders with filtering and pagination
 */
export async function getOrders(
  db: DrizzleD1Database<typeof schema>,
  params: GetOrdersParams
): Promise<GetOrdersResponse> {
  const {
    traderId,
    symbol,
    side,
    status,
    startTime,
    endTime,
    limit = 500,
    offset = 0,
  } = params;

  // Build where conditions
  const conditions = [];
  if (traderId) {
    conditions.push(eq(orders.traderId, traderId));
  }
  if (symbol) {
    conditions.push(eq(orders.symbol, symbol));
  }
  if (side) {
    conditions.push(eq(orders.side, side));
  }
  if (status) {
    conditions.push(eq(orders.status, status));
  }
  if (startTime) {
    conditions.push(gte(orders.time, startTime));
  }
  if (endTime) {
    conditions.push(lte(orders.time, endTime));
  }

  const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

  // Get total count
  const [{ value: total }] = await db
    .select({ value: count() })
    .from(orders)
    .where(whereClause);

  // Import traders schema for join

  // Get orders with pagination and trader information
  const ordersList = await db
    .select({
      // Order fields
      id: orders.id,
      traderId: orders.traderId,
      orderId: orders.orderId,
      clientOrderId: orders.clientOrderId,
      symbol: orders.symbol,
      side: orders.side,
      type: orders.type,
      positionSide: orders.positionSide,
      status: orders.status,
      timeInForce: orders.timeInForce,
      price: orders.price,
      avgPrice: orders.avgPrice,
      stopPrice: orders.stopPrice,
      activatePrice: orders.activatePrice,
      priceRate: orders.priceRate,
      origQty: orders.origQty,
      executedQty: orders.executedQty,
      cumQuote: orders.cumQuote,
      reduceOnly: orders.reduceOnly,
      closePosition: orders.closePosition,
      priceProtect: orders.priceProtect,
      workingType: orders.workingType,
      origType: orders.origType,
      time: orders.time,
      updateTime: orders.updateTime,
      createdAt: orders.createdAt,
      updatedAt: orders.updatedAt,
      // Trader fields
      traderName: traders.name,
    })
    .from(orders)
    .leftJoin(traders, eq(orders.traderId, traders.id))
    .where(whereClause)
    .orderBy(desc(orders.time))
    .limit(limit)
    .offset(offset);

  return {
    orders: ordersList,
    total,
    limit,
    offset,
  };
}

/**
 * Get a single order by ID
 */
export async function getOrderById(
  db: DrizzleD1Database<typeof schema>,
  id: string
) {
  const [order] = await db.select().from(orders).where(eq(orders.id, id));
  return order || null;
}

/**
 * Get a single order by exchange order ID and trader
 */
export async function getOrderByExchangeId(
  db: DrizzleD1Database<typeof schema>,
  traderId: string,
  orderId: string
) {
  const [order] = await db
    .select()
    .from(orders)
    .where(and(eq(orders.traderId, traderId), eq(orders.orderId, orderId)));
  return order || null;
}

/**
 * Update an order's status and execution details
 */
export async function updateOrder(
  db: DrizzleD1Database<typeof schema>,
  id: string,
  data: UpdateOrderInput
) {
  const updateData: Record<string, any> = {
    updatedAt: new Date().toISOString(),
  };

  if (data.status !== undefined) updateData.status = data.status;
  if (data.executedQty !== undefined) updateData.executedQty = data.executedQty;
  if (data.avgPrice !== undefined) updateData.avgPrice = data.avgPrice;
  if (data.cumQuote !== undefined) updateData.cumQuote = data.cumQuote;
  if (data.updateTime !== undefined) updateData.updateTime = data.updateTime;

  const [updated] = await db
    .update(orders)
    .set(updateData)
    .where(eq(orders.id, id))
    .returning();

  return updated || null;
}

/**
 * Batch import orders from exchange API
 * This will skip orders that already exist (based on orderId + traderId)
 */
export async function importOrders(
  db: DrizzleD1Database<typeof schema>,
  input: ImportOrdersInput
): Promise<ImportOrdersResponse> {
  let imported = 0;
  let skipped = 0;
  const errors: string[] = [];

  for (const orderData of input.orders) {
    try {
      // Check if order already exists
      const existing = await getOrderByExchangeId(
        db,
        input.traderId,
        orderData.orderId
      );

      if (existing) {
        skipped++;
        continue;
      }

      // Create new order
      await createOrder(db, {
        ...orderData,
        traderId: input.traderId,
      });
      imported++;
    } catch (error) {
      errors.push(
        `Failed to import order ${orderData.orderId}: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  }

  return {
    imported,
    skipped,
    errors,
  };
}

/**
 * Get orders grouped by symbol for a trader
 */
export async function getOrdersBySymbol(
  db: DrizzleD1Database<typeof schema>,
  traderId: string
) {
  const ordersList = await db
    .select({
      symbol: orders.symbol,
      totalOrders: count(),
      buyOrders: sql<number>`SUM(CASE WHEN ${orders.side} = 'BUY' THEN 1 ELSE 0 END)`,
      sellOrders: sql<number>`SUM(CASE WHEN ${orders.side} = 'SELL' THEN 1 ELSE 0 END)`,
      filledOrders: sql<number>`SUM(CASE WHEN ${orders.status} = 'FILLED' THEN 1 ELSE 0 END)`,
      canceledOrders: sql<number>`SUM(CASE WHEN ${orders.status} = 'CANCELED' THEN 1 ELSE 0 END)`,
    })
    .from(orders)
    .where(eq(orders.traderId, traderId))
    .groupBy(orders.symbol);

  return ordersList;
}

/**
 * Get recent orders for a trader
 */
export async function getRecentOrders(
  db: DrizzleD1Database<typeof schema>,
  traderId: string,
  limit: number = 50
) {
  const ordersList = await db
    .select()
    .from(orders)
    .where(eq(orders.traderId, traderId))
    .orderBy(desc(orders.time))
    .limit(limit);

  return ordersList;
}

/**
 * Get latest orders across all traders or for a specific trader
 * Orders are sorted by time in descending order (newest first)
 * Includes trader information
 */
export async function getLatestOrders(
  db: DrizzleD1Database<typeof schema>,
  params: {
    traderId?: string;
    limit?: number;
  } = {}
) {
  const { traderId, limit = 20 } = params;

  // Import traders schema
  const { traders } = await import("~/features/traders/database/schema");

  // Build query with trader join
  let query = db
    .select({
      // Order fields
      id: orders.id,
      traderId: orders.traderId,
      orderId: orders.orderId,
      clientOrderId: orders.clientOrderId,
      symbol: orders.symbol,
      side: orders.side,
      type: orders.type,
      positionSide: orders.positionSide,
      status: orders.status,
      timeInForce: orders.timeInForce,
      price: orders.price,
      avgPrice: orders.avgPrice,
      stopPrice: orders.stopPrice,
      activatePrice: orders.activatePrice,
      priceRate: orders.priceRate,
      origQty: orders.origQty,
      executedQty: orders.executedQty,
      cumQuote: orders.cumQuote,
      reduceOnly: orders.reduceOnly,
      closePosition: orders.closePosition,
      priceProtect: orders.priceProtect,
      workingType: orders.workingType,
      origType: orders.origType,
      time: orders.time,
      updateTime: orders.updateTime,
      createdAt: orders.createdAt,
      updatedAt: orders.updatedAt,
      // Trader fields
      traderName: traders.name,
    })
    .from(orders)
    .leftJoin(traders, eq(orders.traderId, traders.id));

  if (traderId) {
    query = query.where(eq(orders.traderId, traderId)) as any;
  }

  const ordersList = await query.orderBy(desc(orders.time)).limit(limit);

  return ordersList;
}

/**
 * Delete orders older than a certain date (for cleanup)
 */
export async function deleteOldOrders(
  db: DrizzleD1Database<typeof schema>,
  beforeTimestamp: number
) {
  const result = await db
    .delete(orders)
    .where(lte(orders.time, beforeTimestamp))
    .returning({ id: orders.id });

  return result.length;
}
