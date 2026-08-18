"use client";

import { useState, useEffect } from "react";
import { Doughnut } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartOptions,
} from "chart.js";
import { getBaseHttpUrl } from "@/utils/api";

ChartJS.register(ArcElement, Tooltip, Legend);

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

interface AssetAllocationChartProps {
  asOfDate?: string;
  currency?: string;
}

export function AssetAllocationChart({ asOfDate, currency = "INR" }: AssetAllocationChartProps) {
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
      const baseUrl = await getBaseHttpUrl();
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
      setError("Failed to load asset allocation");
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
        <p className="text-gray-500">Loading allocation...</p>
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
            : "No asset data available. Add assets to see allocation."}
        </p>
      </div>
    );
  }

  const chartData = {
    labels: data.breakdown.map((item) => item.name),
    datasets: [
      {
        data: data.breakdown.map((item) => item.value),
        backgroundColor: [
          "#5b8def",
          "#8b5cf6",
          "#f59e0b",
          "#22c55e",
          "#ec4899",
          "#06b6d4",
          "#84cc16",
          "#ef4444",
        ],
        borderWidth: 0,
        borderColor: "#ffffff",
      },
    ],
  };

  const options: ChartOptions<"doughnut"> = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "75%",
    plugins: {
      legend: {
        position: "right",
        labels: {
          padding: 12,
          font: {
            size: 11,
          },
          usePointStyle: true,
          pointStyle: "circle",
          generateLabels: (chart) => {
            const datasets = chart.data.datasets;
            if (datasets.length > 0) {
              return chart.data.labels?.map((label, i) => {
                return {
                  text: `${label}`,
                  fillStyle: (datasets[0].backgroundColor as string[])[i],
                  hidden: false,
                  index: i,
                };
              }) || [];
            }
            return [];
          },
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.label || "";
            const value = context.parsed;
            const percentage = data.breakdown[context.dataIndex].percentage;
            return `${label}: ${formatCurrency(value, data.currency)} (${percentage}%)`;
          },
        },
      },
    },
  };

  return (
    <div className="h-64">
      {data.excluded_count > 0 && (
        <p className="text-xs text-amber-600 mb-1">
          {data.excluded_count} account(s) excluded — exchange rate unavailable for {currency}.
        </p>
      )}
      <Doughnut data={chartData} options={options} />
    </div>
  );
}
