import { useQuery } from "@tanstack/react-query";

/**
 * Query keys for trader portfolios
 */
export const traderPortfolioKeys = {
  all: ["trader-portfolios"] as const,
  list: () => [...traderPortfolioKeys.all, "list"] as const,
};

/**
 * Enriched instrument position (with computed notional as number)
 */
export interface EnrichedInstrumentPosition {
  symbol: string;
  positionAmt: string;
  entryPrice: string;
  markPrice: string;
  unRealizedProfit: string;
  liquidationPrice: string;
  leverage: string;
  positionSide: "BOTH" | "LONG" | "SHORT";
  notional: number; // Enriched by backend (computed)
  marginType: string;
  isolatedMargin: string;
  isAutoAddMargin: string;
  isolatedWallet: string;
  updateTime: number;
}

/**
 * Position record with aggregated metrics
 */
export interface PositionRecord {
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
 * Trader portfolio data
 */
export interface TraderPortfolioData {
  traderId: string;
  traderName: string;
  records: PositionRecord[];
}

/**
 * API response structure
 */
export interface TraderPortfolioResponse {
  success: boolean;
  data?: {
    traders: TraderPortfolioData[];
    timeRange: {
      start: string;
      end: string;
    };
  };
  error?: string;
  code?: string;
}

/**
 * Computed portfolio for display
 */
export interface ComputedPortfolio {
  traderId: string;
  traderName: string;
  totalAssets: number;
  todayPnl: number;
  positions: Array<{
    symbol: string;
    asset: number; // Total value of this position
    assetPercent: number; // Percentage of total assets
    pnl: number; // Unrealized P&L
    direction: "long" | "short";
    quantity: number;
    entryPrice: number;
    leverage: number;
  }>;
}

/**
 * Fetch all trader portfolios from API
 */
async function fetchTraderPortfolios(): Promise<TraderPortfolioResponse> {
  // Fetch the latest records (last 1 day to get current positions)
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000); // Last 24 hours

  const searchParams = new URLSearchParams({
    start: start.toISOString(),
    end: end.toISOString(),
  });

  const url = `/api/v1/traders/pnl?${searchParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch trader portfolios: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Compute portfolio summary from raw trader data
 */
function computePortfolio(trader: TraderPortfolioData): ComputedPortfolio | null {
  // Get the latest record (most recent position snapshot)
  const latestRecord = trader.records[trader.records.length - 1];

  if (!latestRecord) {
    return null;
  }

  const { accountBalance, accountBalanceDelta, positions } = latestRecord;

  // Calculate total assets (account balance + total unrealized PnL)
  const totalUnrealizedPnl = positions.reduce(
    (sum, pos) => sum + parseFloat(pos.unRealizedProfit || "0"),
    0
  );
  const totalAssets = accountBalance + totalUnrealizedPnl;

  // Transform positions for display
  const portfolioPositions = positions.map((pos) => {
    const unRealizedProfit = parseFloat(pos.unRealizedProfit || "0");
    const positionAmt = parseFloat(pos.positionAmt || "0");
    const entryPrice = parseFloat(pos.entryPrice || "0");
    const leverage = parseFloat(pos.leverage || "1");

    // notional is already computed and converted to number by backend
    const assetValue = pos.notional + unRealizedProfit;
    const assetPercent = totalAssets > 0 ? (assetValue / totalAssets) * 100 : 0;

    // Determine direction based on positionAmt: positive means long, negative means short
    const direction: "long" | "short" = positionAmt >= 0 ? "long" : "short";

    return {
      symbol: pos.symbol,
      asset: assetValue,
      assetPercent,
      pnl: unRealizedProfit,
      direction,
      quantity: Math.abs(positionAmt),
      entryPrice,
      leverage,
    };
  });

  // Sort positions by asset value (descending)
  portfolioPositions.sort((a, b) => b.asset - a.asset);

  return {
    traderId: trader.traderId,
    traderName: trader.traderName,
    totalAssets,
    todayPnl: accountBalanceDelta,
    positions: portfolioPositions,
  };
}

/**
 * Hook to fetch and compute all trader portfolios
 *
 * @returns Query result with computed portfolios
 */
export function useTraderPortfolios() {
  return useQuery({
    queryKey: traderPortfolioKeys.list(),
    queryFn: async () => {
      const response = await fetchTraderPortfolios();

      if (!response.success || !response.data) {
        throw new Error(response.error || "Failed to fetch trader portfolios");
      }

      // Compute portfolio for each trader
      const portfolios = response.data.traders
        .map(computePortfolio)
        .filter((p): p is ComputedPortfolio => p !== null);

      return portfolios;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 1000 * 60, // Refetch every minute
  });
}
