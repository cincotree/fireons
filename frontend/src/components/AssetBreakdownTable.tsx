"use client";

import { useState, useEffect } from "react";
import { getBaseHttpUrl } from "@/utils/api";

interface AllocationEntry {
  name: string;
  value: number;
  percentage: number;
  currency: string;
}

interface AllocationResponse {
  total: number;
  currency: string;
  breakdown: AllocationEntry[];
  excluded_count: number;
}

interface AssetBreakdownTableProps {
  asOfDate?: string;
  currency?: string;
}

const CATEGORY_COLORS = [
  "#5b8def",
  "#8b5cf6",
  "#f59e0b",
  "#22c55e",
  "#ec4899",
  "#06b6d4",
  "#84cc16",
  "#ef4444",
];

export function AssetBreakdownTable({ asOfDate, currency = "INR" }: AssetBreakdownTableProps) {
  const [data, setData] = useState<AllocationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAllocation();
  }, [asOfDate, currency]);

  const fetchAllocation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const baseUrl = getBaseHttpUrl();
      const token = localStorage.getItem("token");
      const params = new URLSearchParams({ currency });
      if (asOfDate) params.append("as_of_date", asOfDate);

      const response = await fetch(
        `${baseUrl}/api/allocation?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to fetch asset allocation");
      }

      const allocationData = await response.json();
      setData(allocationData);
    } catch (err) {
      console.error("Error fetching asset allocation:", err);
      setError("Failed to load asset breakdown");
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (value: number, currency: string) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading asset breakdown...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!data || data.breakdown.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">
          {data && data.excluded_count > 0
            ? `${data.excluded_count} account(s) excluded — exchange rate unavailable for ${currency}.`
            : "No asset data available. Add assets to see the breakdown."}
        </p>
      </div>
    );
  }

  return (
    <div>
      {data.excluded_count > 0 && (
        <p className="text-xs text-amber-600 mb-2">
          {data.excluded_count} account(s) excluded — exchange rate unavailable for {currency}.
        </p>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
            <th className="pb-2 font-medium">Category</th>
            <th className="pb-2 font-medium text-right">%</th>
            <th className="pb-2 font-medium text-right">Market Value</th>
          </tr>
        </thead>
        <tbody>
          {data.breakdown.map((item, index) => {
            const color = CATEGORY_COLORS[index % CATEGORY_COLORS.length];
            return (
              <tr key={item.name} className="border-b border-gray-100 last:border-0">
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="font-medium text-gray-900">{item.name}</span>
                  </div>
                </td>
                <td className="py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${item.percentage}%`, backgroundColor: color }}
                      />
                    </div>
                    <span className="w-12 tabular-nums text-gray-600">{item.percentage}%</span>
                  </div>
                </td>
                <td className="py-3 text-right font-medium tabular-nums text-gray-900">
                  {formatCurrency(item.value, data.currency)}
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-gray-200 font-semibold text-gray-900">
            <td className="pt-3">Total</td>
            <td className="pt-3 text-right tabular-nums">100%</td>
            <td className="pt-3 text-right tabular-nums">{formatCurrency(data.total, data.currency)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
