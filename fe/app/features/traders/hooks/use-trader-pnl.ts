import { useQuery } from "@tanstack/react-query";

export const traderPnlKeys = {
  all: ["traders", "pnl"] as const,
  list: (params?: ResolvedListTraderPnlParams) =>
    [...traderPnlKeys.all, "list", params] as const,
};

export type ListTraderPnlParams = {
  trader?: string; // Single trader ID filter
  start?: string | Date;
  end?: string | Date;
};

type ResolvedListTraderPnlParams = {
  trader?: string;
  start?: string;
  end?: string;
};

/**
 * Instrument position with enriched data
 */
export type InstrumentPosition = {
  symbol: string;
  leverage: number;
  direction: "long" | "short";
  quantity: number;
  entryPrice: number;
  unrealizedPnl: number;
  notional: number; // Calculated value
};

/**
 * Position record with aggregated metrics
 */
export type PositionRecord = {
  recordId: string;
  timestamp: string;
  accountBalance: number;
  accountBalanceDelta: number;
  positions: InstrumentPosition[];
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
};

/**
 * Trader PnL data
 */
export type TraderPnlData = {
  traderId: string;
  traderName: string;
  records: PositionRecord[];
};

export type TraderPnlResponse = {
  success: boolean;
  data?: {
    traders: TraderPnlData[];
    timeRange: {
      start: string;
      end: string;
    };
  };
  error?: string;
  code?: string;
  details?: unknown;
};

function normalizeDateParam(
  name: "start" | "end",
  value?: string | Date
): string | undefined {
  if (value == null) {
    return undefined;
  }

  const date =
    value instanceof Date
      ? value
      : new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new Error(`Invalid ${name} date parameter provided to useTraderPnl`);
  }

  return date.toISOString();
}

function resolveTraderPnlParams(
  params?: ListTraderPnlParams
): ResolvedListTraderPnlParams | undefined {
  if (!params) return undefined;

  const resolved: ResolvedListTraderPnlParams = {};

  if (params.trader) {
    resolved.trader = params.trader;
  }

  const start = normalizeDateParam("start", params.start);
  if (start) {
    resolved.start = start;
  }

  const end = normalizeDateParam("end", params.end);
  if (end) {
    resolved.end = end;
  }

  if (
    resolved.trader === undefined &&
    resolved.start === undefined &&
    resolved.end === undefined
  ) {
    return undefined;
  }

  return resolved;
}

async function fetchTraderPnl(
  params?: ResolvedListTraderPnlParams
): Promise<TraderPnlResponse> {
  const searchParams = new URLSearchParams();

  if (params?.trader) {
    searchParams.set("trader", params.trader);
  }
  if (params?.start) {
    searchParams.set("start", params.start);
  }
  if (params?.end) {
    searchParams.set("end", params.end);
  }

  const url = `/api/v1/traders/pnl${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch trader PnL: ${response.statusText}`);
  }

  return response.json();
}

export function useTraderPnl(params?: ListTraderPnlParams) {
  const resolvedParams = resolveTraderPnlParams(params);

  return useQuery({
    queryKey: traderPnlKeys.list(resolvedParams),
    queryFn: () => fetchTraderPnl(resolvedParams),
    staleTime: 1000 * 5, // 5 minutes
  });
}
