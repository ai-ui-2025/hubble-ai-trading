import { z } from "zod";

export const listTraderPnlQuerySchema = z.object({
  trader: z.string().optional(),
  start: z.string().datetime().optional(),
  end: z.string().datetime().optional(),
});

export type ListTraderPnlQuery = z.infer<typeof listTraderPnlQuerySchema>;
