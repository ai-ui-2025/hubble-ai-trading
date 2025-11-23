import { sqliteTable, text, real, index } from "drizzle-orm/sqlite-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { traders } from "~/features/traders/database/schema";
import { analysisRecords } from "~/features/analysis-team/database/schema";

/**
 * Position records table
 * Stores trader's current position snapshots and account balances
 */
export const positionRecords = sqliteTable(
  "position_records",
  {
    // Primary key
    id: text("id")
      .primaryKey()
      .$defaultFn(() => crypto.randomUUID()),
    // Associated trader
    traderId: text("trader_id")
      .notNull()
      .references(() => traders.id, { onDelete: "restrict" }),
    // Round ID, can be null
    recordId: text("record_id"),
    // Position information (JSON array string)
    // Structure: [{ symbol: string, leverage: number, direction: 'long'|'short', quantity: number, entryPrice: number, unrealizedPnl: number }]
    positions: text("positions").notNull(),
    // Account balance
    accountBalance: real("account_balance").notNull(),
    // Created at timestamp
    createdAt: text("created_at")
      .notNull()
      .$defaultFn(() => new Date().toISOString()),
    // Updated at timestamp
    updatedAt: text("updated_at")
      .notNull()
      .$defaultFn(() => new Date().toISOString()),
  },
  (table) => ({
    // Index for querying by trader and time
    traderTimeIdx: index("idx_position_records_trader_created").on(
      table.traderId,
      table.createdAt
    ),
  })
);

export const insertPositionRecordSchema = createInsertSchema(positionRecords, {
  traderId: () => z.string().min(1),
  recordId: () => z.string().min(1).optional(),
  positions: () => z.string().min(1),
  accountBalance: () => z.number().finite(),
  createdAt: () => z.string().datetime().optional(),
  updatedAt: () => z.string().datetime().optional(),
});

export const selectPositionRecordSchema = createSelectSchema(positionRecords);
