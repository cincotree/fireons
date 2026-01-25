"use client";

import { X, TrendingUp, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Line } from "react-chartjs-2";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
} from "chart.js";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

interface AccountDetailPanelProps {
    account: any;
    onClose: () => void;
}

export function AccountDetailPanel({ account, onClose }: AccountDetailPanelProps) {
    if (!account) return null;

    // Mock history data for this specific account
    const historyData = {
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        datasets: [{
            label: "Balance History",
            data: [
                account.balance * 0.9,
                account.balance * 0.92,
                account.balance * 0.95,
                account.balance * 0.94,
                account.balance * 0.98,
                account.balance
            ],
            borderColor: account.type === 'liability' ? '#EF4444' : '#10B981',
            tension: 0.4,
            pointRadius: 2,
        }]
    };

    const options = {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            x: { display: false },
            y: { display: false }
        }
    };

    return (
        <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-xl border-l border-slate-200 p-6 z-50 transform transition-transform duration-300 ease-in-out">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h2 className="text-xl font-bold text-slate-900">{account.name}</h2>
                    <p className="text-sm text-slate-500 font-mono">{account.id}</p>
                </div>
                <Button variant="ghost" size="icon" onClick={onClose}>
                    <X className="w-5 h-5" />
                </Button>
            </div>

            <div className="mb-8">
                <p className="text-sm text-slate-500 mb-1">Current Balance</p>
                <div className="text-3xl font-bold text-slate-900">
                    {new Intl.NumberFormat('en-US', { style: 'currency', currency: account.currency }).format(account.balance)}
                </div>
            </div>

            <div className="mb-8 h-48 bg-slate-50 rounded-lg p-4 border border-slate-100">
                <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-4 h-4 text-slate-400" />
                    <span className="text-xs font-semibold text-slate-500 uppercase">Growth Trend</span>
                </div>
                <div className="h-32">
                    <Line options={options} data={historyData} />
                </div>
            </div>

            <div className="space-y-4">
                <h3 className="font-semibold text-slate-900">Notes</h3>
                <textarea
                    className="w-full h-32 p-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-brand-900 outline-none resize-none"
                    placeholder="Add details about this account, interest rates, or login info..."
                />
                <Button className="w-full bg-brand-900 hover:bg-brand-900/90 text-white gap-2">
                    <Save className="w-4 h-4" /> Save Notes
                </Button>
            </div>

            <div className="mt-8 pt-8 border-t border-slate-100">
                <Button variant="destructive" className="w-full gap-2">
                    Close Account / Archive
                </Button>
            </div>
        </div>
    );
}
