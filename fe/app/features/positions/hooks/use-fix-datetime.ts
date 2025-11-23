import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "~/lib/api-client";

export const fixDateTimeKeys = {
  all: ["admin", "position-records", "fix-datetime"] as const,
  list: () => [...fixDateTimeKeys.all, "list"] as const,
};

export interface RecordToFix {
  id: string;
  traderId: string;
  currentCreatedAt: string;
  fixedCreatedAt: string;
}

export interface FixDateTimeData {
  totalRecords: number;
  recordsToFix: number;
  records: RecordToFix[];
}

export interface FixDateTimeResponse {
  success: boolean;
  data?: FixDateTimeData;
  error?: string;
  code?: string;
}

export interface FixAllResponse {
  success: boolean;
  data?: {
    fixedCount: number;
    message: string;
  };
  error?: string;
  code?: string;
}

/**
 * 获取需要修复的记录列表
 */
async function fetchRecordsToFix(): Promise<FixDateTimeData> {
  const response = await apiGet<FixDateTimeData>("admin/position-records/fix-datetime");
  return response;
}

/**
 * Hook to fetch records that need datetime fix
 */
export function useRecordsToFix() {
  return useQuery({
    queryKey: fixDateTimeKeys.list(),
    queryFn: fetchRecordsToFix,
    staleTime: 0, // 不缓存，每次都获取最新数据
  });
}

/**
 * 修复全部记录
 */
async function fixAllRecords(): Promise<FixAllResponse["data"]> {
  return apiPost<FixAllResponse["data"]>("admin/position-records/fix-datetime", {
    fixAll: true,
  });
}

/**
 * 修复选中的记录
 */
async function fixSelectedRecords(recordIds: string[]): Promise<FixAllResponse["data"]> {
  return apiPost<FixAllResponse["data"]>("admin/position-records/fix-datetime", {
    recordIds,
  });
}

/**
 * Hook to fix all records
 */
export function useFixAllRecords() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: fixAllRecords,
    onSuccess: () => {
      // 修复成功后，重新获取列表
      queryClient.invalidateQueries({ queryKey: fixDateTimeKeys.all });
    },
  });
}

/**
 * Hook to fix selected records
 */
export function useFixSelectedRecords() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: fixSelectedRecords,
    onSuccess: () => {
      // 修复成功后，重新获取列表
      queryClient.invalidateQueries({ queryKey: fixDateTimeKeys.all });
    },
  });
}
