"use client";

import { Doughnut } from "react-chartjs-2";
import {
    Chart as ChartJS,
    ArcElement,
    Tooltip,
    Legend,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

interface AssetAllocationProps {
    data: { name: string; value: number }[];
}

export function AssetAllocation({ data }: AssetAllocationProps) {
    const chartData = {
        labels: data.map((d) => d.name),
        datasets: [
            {
                data: data.map((d) => d.value),
                backgroundColor: [
                    "#3b82f6", // blue-500
                    "#10b981", // emerald-500
                    "#f59e0b", // amber-500
                    "#8b5cf6", // violet-500
                    "#ec4899", // pink-500
                    "#6366f1", // indigo-500
                ],
                borderWidth: 0,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: "right" as const,
                labels: {
                    usePointStyle: true,
                    padding: 20,
                    font: {
                        size: 12
                    }
                }
            },
            tooltip: {
                callbacks: {
                    label: function (context: any) {
                        let label = context.label || '';
                        if (label) {
                            label += ': ';
                        }
                        const value = context.parsed;
                        const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1) + "%";
                        return label + new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: "compact" }).format(value) + ` (${percentage})`;
                    }
                }
            }
        },
        cutout: "70%",
    };

    return (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-none h-[400px]">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Asset Allocation</h3>
            <div className="h-[320px] flex items-center justify-center">
                <Doughnut options={options} data={chartData} />
            </div>
        </div>
    );
}
