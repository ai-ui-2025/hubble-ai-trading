import type { z } from "zod";
import type {
  insertPositionRecordSchema,
  selectPositionRecordSchema,
} from "./schema";

export type PositionRecord = z.infer<typeof selectPositionRecordSchema>;
export type InsertPositionRecord = z.infer<typeof insertPositionRecordSchema>;

/**
 * Single instrument position information structure (matches Binance Futures API)
 */
export interface InstrumentPosition {
  symbol: string; // Instrument name
  positionAmt: string; // Position quantity (string format)
  entryPrice: string; // Average entry price (string format)
  markPrice: string; // Mark price (string format)
  unRealizedProfit: string; // Unrealized profit/loss (string format)
  liquidationPrice: string; // Liquidation price
  leverage: string; // Leverage multiplier (string format)
  maxNotionalValue: string; // Maximum notional value
  marginType: string; // Margin type: cross/isolated
  isolatedMargin: string; // Isolated margin
  isAutoAddMargin: string; // Whether to auto-add margin
  positionSide: "BOTH" | "LONG" | "SHORT"; // Position direction
  notional: string; // Notional value (string format)
  isolatedWallet: string; // Isolated wallet balance
  updateTime: number; // Update timestamp
}
