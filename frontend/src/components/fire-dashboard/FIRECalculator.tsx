"use client";

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { calculateFireProjection, FireInputs } from "@/lib/fireUtils";
import { Line } from "react-chartjs-2";

export function FIRECalculator() {
    const [inputs, setInputs] = useState<FireInputs>({
        currentAge: 30,
        retirementAge: 45,
        annualExpenses: 60000,
        currentNetWorth: 215000,
        annualSavings: 45000,
        expectedReturn: 7,
        inflationRate: 3,
        safeWithdrawalRate: 4,
    });

    const projection = useMemo(() => calculateFireProjection(inputs), [inputs]);
    const fiYear = projection.find(p => p.isFi);
    const yearsToFi = fiYear ? fiYear.year - new Date().getFullYear() : "> 50";

    const chartData = {
        labels: projection.map(p => p.age),
        datasets: [
            {
                label: "Projected Net Worth",
                data: projection.map(p => p.netWorth),
                borderColor: "rgb(16, 185, 129)", // emerald-500
                backgroundColor: "rgba(16, 185, 129, 0.1)",
                fill: true,
                tension: 0.4,
            },
            {
                label: "FI Target",
                data: projection.map(p => p.target),
                borderColor: "rgb(239, 68, 68)", // red-500
                borderDash: [5, 5],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
            }
        ]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: "bottom" as const },
            tooltip: {
                mode: "index" as const,
                intersect: false,
                callbacks: {
                    label: function (context: any) {
                        return context.dataset.label + ": " + new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(context.parsed.y);
                    }
                }
            }
        },
        scales: {
            y: {
                ticks: {
                    callback: function (value: any) {
                        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(value);
                    }
                }
            }
        }
    };

    const InputField = ({ label, value, onChange, prefix = "", suffix = "" }: any) => (
        <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
            <div className="relative rounded-md shadow-sm">
                {prefix && (
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                        <span className="text-gray-500 sm:text-sm">{prefix}</span>
                    </div>
                )}
                <input
                    type="number"
                    className={`block w-full rounded-md border-0 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 ${prefix ? 'pl-7' : 'pl-3'} ${suffix ? 'pr-8' : 'pr-3'}`}
                    value={value}
                    onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
                />
                {suffix && (
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                        <span className="text-gray-500 sm:text-sm">{suffix}</span>
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <div className="mb-6">
                <h3 className="text-lg font-semibold text-slate-900">FIRE Planner</h3>
                <p className="text-sm text-slate-500">Simulate your path to Financial Independence</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-1 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <InputField
                            label="Current Age"
                            value={inputs.currentAge}
                            onChange={(v: number) => setInputs({ ...inputs, currentAge: v })}
                        />
                        <InputField
                            label="Target Age"
                            value={inputs.retirementAge}
                            onChange={(v: number) => setInputs({ ...inputs, retirementAge: v })}
                        />
                    </div>
                    <InputField
                        label="Annual Expenses (Today)"
                        value={inputs.annualExpenses}
                        prefix="$"
                        onChange={(v: number) => setInputs({ ...inputs, annualExpenses: v })}
                    />
                    <InputField
                        label="Current Annual Savings"
                        value={inputs.annualSavings}
                        prefix="$"
                        onChange={(v: number) => setInputs({ ...inputs, annualSavings: v })}
                    />
                    <div className="grid grid-cols-2 gap-4">
                        <InputField
                            label="Expected Return"
                            value={inputs.expectedReturn}
                            suffix="%"
                            onChange={(v: number) => setInputs({ ...inputs, expectedReturn: v })}
                        />
                        <InputField
                            label="Inflation"
                            value={inputs.inflationRate}
                            suffix="%"
                            onChange={(v: number) => setInputs({ ...inputs, inflationRate: v })}
                        />
                    </div>
                </div>

                <div className="lg:col-span-2">
                    <div className="bg-slate-50 rounded-lg p-4 mb-4 flex items-center justify-between">
                        <div>
                            <p className="text-sm text-slate-500">Freedom Year</p>
                            <p className="text-2xl font-bold text-slate-900">{fiYear?.year || "N/A"}</p>
                        </div>
                        <div>
                            <p className="text-sm text-slate-500">Years Remaining</p>
                            <p className="text-2xl font-bold text-blue-600">{yearsToFi}</p>
                        </div>
                        <div>
                            <p className="text-sm text-slate-500">FI Number</p>
                            <p className="text-2xl font-bold text-slate-900">
                                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: "compact" }).format(fiYear?.target || 0)}
                            </p>
                        </div>
                    </div>
                    <div className="h-[300px]">
                        <Line options={options} data={chartData} />
                    </div>
                </div>
            </div>
        </div>
    );
}
