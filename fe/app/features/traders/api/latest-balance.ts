import type { DatabaseType } from "~/lib/db-utils";

export interface LatestBalanceApiDeps {
  db: DatabaseType;
  env: Env;
}

/**
 * Latest balance data for a trader
 */
export interface TraderLatestBalance {
  traderId: string;
  accountBalance: number;
  timestamp: string;
}

/**
 * Latest balance response structure
 */
export interface LatestBalanceResponse {
  traders: TraderLatestBalance[];
  timestamp: string;
}

/**
 * Get latest account balance for all traders from database
 * Retrieves real balance by querying each trader's latest position record
 *
 * @param deps - API dependencies (db, env)
 * @returns Promise with latest balance data for all traders
 */
export async function getLatestBalance(
  deps: LatestBalanceApiDeps
): Promise<LatestBalanceResponse> {
  const { db } = deps;

  // Query all traders
  const allTraders = await db.query.traders.findMany();

  // Get latest position record for each trader, extract real accountBalance
  const now = new Date().toISOString();
  const traders: TraderLatestBalance[] = await Promise.all(
    allTraders.map(async (trader) => {
      // Query latest position record for this trader
      const latestRecord = await db.query.positionRecords.findFirst({
        where: (positionRecords, { eq }) => eq(positionRecords.traderId, trader.id),
        orderBy: (positionRecords, { desc }) => [desc(positionRecords.createdAt)],
      });

      // If record exists, use real accountBalance; otherwise return 0
      const accountBalance = latestRecord?.accountBalance ?? 0;

      return {
        traderId: trader.id,
        accountBalance: Math.round(accountBalance * 100) / 100, // Keep 2 decimal places
        timestamp: latestRecord?.createdAt ?? now,
      };
    })
  );

  return {
    traders,
    timestamp: now,
  };
}
