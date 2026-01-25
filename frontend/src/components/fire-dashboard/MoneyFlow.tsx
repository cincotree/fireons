"use client";

import { ArrowRight } from "lucide-react";

export function MoneyFlow() {
    // Mock Data
    const data = {
        income: 120000,
        taxes: 30000,
        expenses: 45000,
        savings: 45000,
        investments: {
            stocks: 30000,
            realEstate: 10000,
            cash: 5000
        }
    };

    const formatK = (num: number) => "$" + (num / 1000).toFixed(0) + "k";

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <h3 className="text-lg font-semibold text-slate-900 mb-6">Annual Money Flow (2025)</h3>

            <div className="relative flex justify-between items-center space-x-4">
                {/* Source: Income */}
                <div className="flex flex-col justify-center h-48 w-1/4 space-y-2">
                    <div className="bg-emerald-100 border border-emerald-200 p-4 rounded-lg text-center">
                        <div className="text-sm text-emerald-800 font-medium">Income</div>
                        <div className="text-xl font-bold text-emerald-900">{formatK(data.income)}</div>
                    </div>
                </div>

                {/* Arrows */}
                <div className="flex flex-col h-48 justify-around py-4">
                    <ArrowRight className="text-slate-300" />
                    <ArrowRight className="text-slate-300" />
                    <ArrowRight className="text-slate-300" />
                </div>

                {/* Allocation */}
                <div className="flex flex-col justify-between h-56 w-1/4 space-y-2">
                    <div className="bg-slate-100 border border-slate-200 p-3 rounded-lg text-center flex-1 flex flex-col justify-center">
                        <div className="text-xs text-slate-600">Taxes ({((data.taxes / data.income) * 100).toFixed(0)}%)</div>
                        <div className="font-bold text-slate-800">{formatK(data.taxes)}</div>
                    </div>
                    <div className="bg-orange-100 border border-orange-200 p-3 rounded-lg text-center flex-1 flex flex-col justify-center">
                        <div className="text-xs text-orange-800">Expenses ({((data.expenses / data.income) * 100).toFixed(0)}%)</div>
                        <div className="font-bold text-orange-900">{formatK(data.expenses)}</div>
                    </div>
                    <div className="bg-blue-100 border border-blue-200 p-3 rounded-lg text-center flex-1 flex flex-col justify-center">
                        <div className="text-xs text-blue-800">Savings ({((data.savings / data.income) * 100).toFixed(0)}%)</div>
                        <div className="font-bold text-blue-900">{formatK(data.savings)}</div>
                    </div>
                </div>

                {/* Arrows */}
                <div className="flex flex-col h-48 justify-end pb-8">
                    <ArrowRight className="text-blue-300" />
                </div>

                {/* Investments Breakdown */}
                <div className="flex flex-col justify-end h-56 w-1/4 space-y-2">
                    <div className="p-2 border-l-2 border-blue-200 pl-4">
                        <div className="text-xs text-slate-500">Stocks</div>
                        <div className="font-semibold text-slate-700">{formatK(data.investments.stocks)}</div>
                    </div>
                    <div className="p-2 border-l-2 border-blue-200 pl-4">
                        <div className="text-xs text-slate-500">Real Estate</div>
                        <div className="font-semibold text-slate-700">{formatK(data.investments.realEstate)}</div>
                    </div>
                    <div className="p-2 border-l-2 border-blue-200 pl-4">
                        <div className="text-xs text-slate-500">Cash</div>
                        <div className="font-semibold text-slate-700">{formatK(data.investments.cash)}</div>
                    </div>
                </div>

            </div>
        </div>
    );
}
