import type { DrizzleD1Database } from "drizzle-orm/d1";
import type * as schema from "@/schema";
import { traders } from "../database/schema";

/**
 * Create new trader
 */
export async function createTrader(
  db: DrizzleD1Database<typeof schema>,
  data: {
    name: string;
    description?: string;
  }
) {
  const [trader] = await db
    .insert(traders)
    .values({
      name: data.name,
      description: data.description,
    })
    .returning();

  return trader;
}

