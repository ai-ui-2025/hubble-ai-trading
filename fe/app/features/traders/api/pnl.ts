import type { DatabaseType } from "~/lib/db-utils";
import { listTraderPositionRecords } from "../lib/server-actions";
import {
  listTraderPnlQuerySchema,
  type ListTraderPnlQuery,
} from "../lib/validation";
import type { InstrumentPosition } from "~/features/positions/database/types";

export interface TraderPnlApiDeps {
  db: DatabaseType;
  env: Env;
}

type ParseResult<TData, TError> =
  | { success: true; data: TData }
  | { success: false; error: TError };

const DEFAULT_TRADER_PNL_RANGE_MS = 30 * 24 * 60 * 60 * 1000;

/**
 * Safely parse JSON string
 */
function parseJsonSafely<T>(value: string | null | undefined): T | null {
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

/**
 * Parse and validate query parameters for trader PnL listing
 */
export function parseListTraderPnlQuery(
  searchParams: URLSearchParams
): ParseResult<ListTraderPnlQuery, unknown> {
  const queryParams = Object.fromEntries(searchParams.entries());
  const parsedQuery = listTraderPnlQuerySchema.safeParse(queryParams);

  if (!parsedQuery.success) {
    return {
      success: false,
      error: parsedQuery.error.flatten(),
    };
  }

  const now = new Date();
  const endDate = parsedQuery.data.end
    ? new Date(parsedQuery.data.end)
    : now;
  const startDate = parsedQuery.data.start
    ? new Date(parsedQuery.data.start)
    : new Date(endDate.getTime() - DEFAULT_TRADER_PNL_RANGE_MS);

  if (startDate.getTime() > endDate.getTime()) {
    return {
      success: false,
      error: {
        formErrors: [],
        fieldErrors: {
          start: ["`start` must be before or equal to `end`"],
        },
      },
    };
  }

  return {
    success: true,
    data: {
      trader: parsedQuery.data.trader,
      start: startDate.toISOString(),
      end: endDate.toISOString(),
    },
  };
}

/**
 * Enriched position with computed notional value
 */
export interface EnrichedInstrumentPosition extends Omit<InstrumentPosition, 'notional'> {
  notional: number; // Computed from positionAmt * markPrice
}

/**
 * Position record with enriched data and aggregated metrics
 */
export interface EnrichedPositionRecord {
  recordId: string;
  timestamp: string;
  accountBalance: number;
  accountBalanceDelta: number;
  positions: EnrichedInstrumentPosition[];
  aggregated: {
    positionCount: number;
    totalUnrealizedPnl: number;
    exposures: {
      long: number;
      short: number;
      net: number;
    };
  };
  createdAt: string;
  updatedAt: string;
}

/**
 * Trader PnL data grouped by trader
 */
export interface TraderPnlData {
  traderId: string;
  traderName: string;
  records: EnrichedPositionRecord[];
}

/**
 * List trader PnL response structure
 */
export interface ListTraderPnlResponse {
  traders: TraderPnlData[];
  timeRange: {
    start: string;
    end: string;
  };
}

/**
 * List trader PnL data based on position records
 *
 * This function:
 * 1. Fetches position records from the database
 * 2. Groups records by trader
 * 3. Enriches each record with calculated metrics (notional, exposures, etc.)
 * 4. Calculates realized PnL delta between consecutive records
 */
export async function listTraderPnl(
  deps: TraderPnlApiDeps,
  query: ListTraderPnlQuery
): Promise<ListTraderPnlResponse> {
  const { db } = deps;
  const records = await listTraderPositionRecords(db, query);

  // Group records by trader
  const traderMap = new Map<
    string,
    {
      traderId: string;
      traderName: string;
      records: EnrichedPositionRecord[];
    }
  >();

  for (const { record, trader } of records) {
    let traderEntry = traderMap.get(trader.id);
    if (!traderEntry) {
      traderEntry = {
        traderId: trader.id,
        traderName: trader.name,
        records: [],
      };
      traderMap.set(trader.id, traderEntry);
    }

    // Parse positions JSON
    const positions = parseJsonSafely<InstrumentPosition[]>(record.positions) ?? [];

    // Calculate aggregated metrics from positions
    let exposureLong = 0;
    let exposureShort = 0;
    let totalUnrealizedPnl = 0;

    const enrichedPositions = positions.map((pos) => {
      // Binance returns strings, need to convert to numbers
      const positionAmt = parseFloat(pos.positionAmt || "0");
      const entryPrice = parseFloat(pos.entryPrice || "0");
      const unRealizedProfit = parseFloat(pos.unRealizedProfit || "0");
      const notionalValue = parseFloat(pos.notional || "0");

      // Determine long/short based on positionSide and positionAmt
      // positionAmt > 0 means long, < 0 means short
      if (positionAmt > 0) {
        exposureLong += notionalValue;
      } else if (positionAmt < 0) {
        exposureShort += Math.abs(notionalValue);
      }

      totalUnrealizedPnl += unRealizedProfit;

      return {
        ...pos,
        notional: notionalValue,
      };
    });

    // Calculate accountBalanceDelta by comparing with previous record
    const previousRecord = traderEntry.records[traderEntry.records.length - 1];
    const previousAccountBalance = previousRecord?.accountBalance ?? 0;
    const accountBalanceDelta = record.accountBalance - previousAccountBalance;

    const enrichedRecord: EnrichedPositionRecord = {
      recordId: record.id,
      timestamp: record.createdAt,
      accountBalance: record.accountBalance,
      accountBalanceDelta,
      positions: enrichedPositions,
      aggregated: {
        positionCount: positions.length,
        totalUnrealizedPnl,
        exposures: {
          long: exposureLong,
          short: exposureShort,
          net: exposureLong - exposureShort,
        },
      },
      createdAt: record.createdAt,
      updatedAt: record.updatedAt,
    };

    traderEntry.records.push(enrichedRecord);
  }

  return {
    traders: Array.from(traderMap.values()).map((entry) => ({
      traderId: entry.traderId,
      traderName: entry.traderName,
      // Sort records by timestamp in descending order (newest first)
      records: entry.records.sort((a, b) =>
        a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0
      ),
    })),
    timeRange: {
      start: query.start || new Date(Date.now() - DEFAULT_TRADER_PNL_RANGE_MS).toISOString(),
      end: query.end || new Date().toISOString(),
    },
  };
}
