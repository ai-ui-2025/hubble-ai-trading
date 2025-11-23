import type { DrizzleD1Database } from "drizzle-orm/d1";
import type * as schema from "@/schema";
import { positionRecords } from "../database/schema";

/**
 * Create a new position record
 */
export async function createPositionRecord(
  db: DrizzleD1Database<typeof schema>,
  data: {
    traderId: string;
    recordId?: string | null;
    positions: string; // JSON string, format: [{ symbol, leverage, direction, quantity, entryPrice, unrealizedPnl }]
    accountBalance: number;
    createdAt?: string;
    updatedAt?: string;
  }
) {
  const now = new Date().toISOString();
  const [record] = await db
    .insert(positionRecords)
    .values({
      traderId: data.traderId,
      recordId: data.recordId ?? null,
      positions: data.positions,
      accountBalance: data.accountBalance,
      createdAt: data.createdAt ?? now,
      updatedAt: data.updatedAt ?? now,
    })
    .returning();

  return record;
}
