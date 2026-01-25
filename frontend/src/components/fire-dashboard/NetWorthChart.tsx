"use client";

import { Line } from "react-chartjs-2";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    ScriptableContext
} from "chart.js";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

interface HistoryData {
    date: string;
    value: number;
    assets: number;
    liabilities: number;
}

export function NetWorthChart({ data }: { data: HistoryData[] }) {
    const chartData = {
        labels: data.map((d) => d.date),
        datasets: [
            {
                label: "Net Worth",
                data: data.map((d) => d.value),
                borderColor: "rgb(16, 185, 129)", // emerald-500
                backgroundColor: (context: ScriptableContext<"line">) => {
                    const ctx = context.chart.ctx;
                    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
                    gradient.addColorStop(0, "rgba(16, 185, 129, 0.4)");
                    gradient.addColorStop(1, "rgba(16, 185, 129, 0.0)");
                    return gradient;
                },
                fill: true,
                tension: 0.4,
                pointRadius: 2,
                pointHoverRadius: 6,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: "top" as const,
                align: "end" as const,
                labels: {
                    usePointStyle: true,
                    boxWidth: 8,
                },
            },
            tooltip: {
                mode: "index" as const,
                intersect: false,
                backgroundColor: "rgba(255, 255, 255, 0.9)",
                titleColor: "#1e293b",
                bodyColor: "#1e293b",
                borderColor: "#e2e8f0",
                borderWidth: 1,
                padding: 10,
                callbacks: {
                    label: function (context: any) {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        if (context.parsed.y !== null) {
                            label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y);
                        }
                        return label;
                    }
                }
            },
        },
        scales: {
            x: {
                grid: {
                    display: false,
                },
                ticks: {
                    maxTicksLimit: 6,
                    color: "#94a3b8",
                },
            },
            y: {
                grid: {
                    color: "#f1f5f9",
                },
                ticks: {
                    color: "#94a3b8",
                    callback: function (value: any) {
                        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(value);
                    }
                },
            },
        },
        interaction: {
            mode: 'nearest' as const,
            axis: 'x' as const,
            intersect: false
        }
    };

    return (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-none h-[400px]">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-slate-900">Growth Trend</h3>
            </div>
            <div className="h-[320px]">
                <Line options={options} data={chartData} />
            </div>
        </div>
    );
}
