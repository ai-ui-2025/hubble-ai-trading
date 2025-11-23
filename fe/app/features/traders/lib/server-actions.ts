import { and, desc, eq, gte, lte } from "drizzle-orm";
import type { SQL } from "drizzle-orm";
import { positionRecords, traders } from "@/schema";
import type { DatabaseType } from "~/lib/db-utils";
import type { ListTraderPnlQuery } from "./validation";

export interface PositionRecordWithTrader {
  record: typeof positionRecords.$inferSelect;
  trader: typeof traders.$inferSelect;
}

export async function listTraderPositionRecords(
  db: DatabaseType,
  query: ListTraderPnlQuery
): Promise<PositionRecordWithTrader[]> {
  const filters: SQL[] = [];

  if (query.start) {
    filters.push(gte(positionRecords.createdAt, query.start));
  }

  if (query.end) {
    filters.push(lte(positionRecords.createdAt, query.end));
  }

  if (query.trader) {
    filters.push(eq(positionRecords.traderId, query.trader));
  }

  const baseQuery = db
    .select({
      record: positionRecords,
      trader: traders,
    })
    .from(positionRecords)
    .innerJoin(traders, eq(positionRecords.traderId, traders.id))
    .orderBy(desc(positionRecords.createdAt));

  const rows = filters.length > 0
    ? await baseQuery.where(and(...filters))
    : await baseQuery;

  return rows;
}
