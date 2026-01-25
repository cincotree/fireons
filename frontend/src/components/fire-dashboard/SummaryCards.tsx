"use client";

import { ArrowUpRight, ArrowDownRight, TrendingUp, Target, DollarSign } from "lucide-react";

interface SummaryCardsProps {
    netWorth: number;
    fiNumber: number;
    monthlyChange: number;
    currency: string;
}

export function SummaryCards({ netWorth, fiNumber, monthlyChange, currency }: SummaryCardsProps) {
    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: currency,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const progress = Math.min(100, Math.max(0, (netWorth / fiNumber) * 100));
    const isPositive = monthlyChange >= 0;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
            {/* Net Worth Card */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-none relative overflow-hidden group hover:border-slate-300 transition-colors">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <DollarSign className="w-16 h-16 text-emerald-600" />
                </div>
                <p className="text-sm font-medium text-slate-500 mb-1">Total Net Worth</p>
                <div className="text-3xl font-bold text-slate-900 tracking-tight">
                    {formatCurrency(netWorth)}
                </div>
                <div className={`flex items-center gap-1 mt-2 text-sm ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {isPositive ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                    <span className="font-medium">{Math.abs(monthlyChange)}%</span>
                    <span className="text-slate-400">vs last month</span>
                </div>
            </div>



            {/* Runway / Years Card */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-none relative overflow-hidden group hover:border-slate-300 transition-colors">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                    <TrendingUp className="w-16 h-16 text-purple-600" />
                </div>
                <p className="text-sm font-medium text-slate-500 mb-1">Est. Time to FIRE</p>
                <div className="text-3xl font-bold text-slate-900 tracking-tight">
                    8.5 Years
                </div>
                <div className="mt-2 text-sm text-slate-500">
                    Based on current savings rate
                </div>
            </div>
        </div>
    );
}
