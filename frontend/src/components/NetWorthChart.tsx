"use client";

import { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { getBaseHttpUrl } from "@/utils/api";

interface NetWorthHistoryEntry {
  date: string;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
}

interface NetWorthChartProps {
  currency?: string;
  startDate?: string;
  endDate?: string;
}

export function NetWorthChart({
  currency = "USD",
  startDate,
  endDate,
}: NetWorthChartProps) {
  const [data, setData] = useState<NetWorthHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory();
  }, [currency, startDate, endDate]);

  const fetchHistory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");
      const params = new URLSearchParams({ currency });
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);

      const response = await fetch(
        `${baseUrl}/api/networth/history?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to fetch net worth history");
      }

      const historyData = await response.json();
      setData(historyData);
    } catch (err) {
      console.error("Error fetching net worth history:", err);
      setError("Failed to load net worth history");
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading chart...</p>
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

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">
          No historical data available. Add balance snapshots to see trends.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <defs>
            <linearGradient id="netWorthGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#86efac" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#86efac" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            style={{ fontSize: "12px" }}
            stroke="#999"
          />
          <YAxis
            tickFormatter={formatCurrency}
            style={{ fontSize: "12px" }}
            stroke="#999"
          />
          <Tooltip
            formatter={(value: number) => formatCurrency(value)}
            labelFormatter={formatDate}
          />
          <Legend
            verticalAlign="top"
            align="right"
            wrapperStyle={{ paddingBottom: "10px" }}
          />
          <Area
            type="monotone"
            dataKey="net_worth"
            name="Net Worth"
            stroke="#4ade80"
            strokeWidth={2}
            fill="url(#netWorthGradient)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
