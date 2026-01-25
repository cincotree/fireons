"use client";

import { useState, useMemo } from "react";
import { Slider } from "@/components/ui/slider";
import { Chart } from "react-chartjs-2";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    ChartData,
    ChartOptions
} from "chart.js";

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

export function AdvancedFireSimulator() {
    const [params, setParams] = useState({
        currentAge: 32,
        currentIncome: 120000,
        currentExpenses: 48000,
        currentPortfolio: 250000,
        incomeGrowth: 3, // %
        expenseInflation: 3, // %
        investmentReturn: 7, // %
        savingsRate: 0, // Calculated dynamically if income > expenses
        withdrawalRate: 4, // %
    });

    // Calculate Projection
    const projection = useMemo(() => {
        const data = [];
        let age = params.currentAge;
        let income = params.currentIncome;
        let expenses = params.currentExpenses;
        let portfolio = params.currentPortfolio;
        let passiveIncome = 0;
        let isFi = false;
        let fiAge = null;

        for (let year = 0; year <= 40; year++) {
            passiveIncome = portfolio * (params.withdrawalRate / 100);

            // Check FI Status: Passive Income > Expenses (Simple Crossover)
            if (!isFi && passiveIncome >= expenses) {
                isFi = true;
                fiAge = age;
            }

            data.push({
                age,
                income: Math.round(income),
                expenses: Math.round(expenses),
                portfolio: Math.round(portfolio),
                passiveIncome: Math.round(passiveIncome),
                isFi
            });

            // Next Year Calc
            age++;

            // Income & Expenses grow
            income = income * (1 + params.incomeGrowth / 100);
            expenses = expenses * (1 + params.expenseInflation / 100);

            // Portfolio grows by return + savings (Income - Expenses)
            const savings = Math.max(0, income - expenses);
            portfolio = (portfolio * (1 + params.investmentReturn / 100)) + savings;
        }
        return { data, fiAge };
    }, [params]);

    // Chart Configuration
    const chartData: ChartData<'bar' | 'line', number[], number> = {
        labels: projection.data.map(d => d.age),
        datasets: [
            {
                type: 'line' as const,
                label: 'Expenses (The Hurdle)',
                data: projection.data.map(d => d.expenses),
                borderColor: 'rgb(239, 68, 68)', // red-500
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                yAxisID: 'y',
                order: 1, // Draw on top
            },
            {
                type: 'line' as const,
                label: 'Passive Income (4% Rule)',
                data: projection.data.map(d => d.passiveIncome),
                borderColor: 'rgb(16, 185, 129)', // emerald-500
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 3,
                fill: true,
                pointRadius: 0,
                yAxisID: 'y',
                order: 2,
            },
            {
                type: 'bar' as const,
                label: 'Portfolio Value',
                data: projection.data.map(d => d.portfolio),
                backgroundColor: 'rgba(59, 130, 246, 0.2)', // blue-500
                yAxisID: 'y1',
                order: 3,
                hidden: true, // Hide by default to keep chart clean, toggleable
            },
        ],
    };

    const options: ChartOptions<'bar' | 'line'> = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: { position: 'top' },
            tooltip: {
                callbacks: {
                    label: function (context: any) {
                        return context.dataset.label + ": " + new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(context.parsed.y);
                    }
                }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { maxTicksLimit: 10 }
            },
            y: {
                type: 'linear' as const,
                display: true,
                position: 'left' as const,
                title: { display: true, text: 'Annual Cashflow ($)' },
                ticks: {
                    callback: function (value: any) {
                        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(value as number);
                    }
                }
            },
            y1: {
                type: 'linear' as const,
                display: true,
                position: 'right' as const,
                title: { display: true, text: 'Portfolio Value ($)' },
                grid: { display: false }, // only show grid for left axis
                ticks: {
                    callback: function (value: any) {
                        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact' }).format(value as number);
                    }
                }
            },
        },
    };

    const InputSlider = ({ label, value, min, max, step, onChange, unit }: any) => (
        <div className="space-y-3">
            <div className="flex justify-between items-center bg-slate-50 p-2 rounded-lg">
                <label className="text-sm font-medium text-slate-700">{label}</label>
                <span className="font-bold text-slate-900 bg-white px-2 py-0.5 rounded shadow-sm border border-slate-100 min-w-[60px] text-center">
                    {typeof value === 'number' && unit === '$' ? (value >= 1000 ? (value / 1000).toFixed(0) + 'k' : value) : value}{unit}
                </span>
            </div>
            <Slider
                min={min}
                max={max}
                step={step}
                value={value}
                onValueChange={onChange}
            />
        </div>
    );

    return (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-none">
            <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                        Cashflow Simulator
                        <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full uppercase tracking-wider">Beta</span>
                    </h3>
                    <p className="text-slate-500 text-sm mt-1">Play with the assumptions to find your crossover point.</p>
                </div>

                <div className="bg-emerald-50 border border-emerald-100 px-4 py-2 rounded-lg text-right">
                    <p className="text-xs text-emerald-600 font-semibold uppercase tracking-wider">Financial Independence At</p>
                    <p className="text-3xl font-bold text-emerald-900">
                        {projection.fiAge ? `Age ${projection.fiAge}` : "Not in range"}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Controls */}
                <div className="lg:col-span-4 space-y-6 bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                    <div className="space-y-4">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest pl-1">Starting Point</p>
                        <InputSlider
                            label="Current Income"
                            value={params.currentIncome}
                            min={30000}
                            max={500000}
                            step={1000}
                            onChange={(v: number) => setParams({ ...params, currentIncome: v })}
                            unit="$"
                        />
                        <InputSlider
                            label="Current Expenses"
                            value={params.currentExpenses}
                            min={12000}
                            max={200000}
                            step={500}
                            onChange={(v: number) => setParams({ ...params, currentExpenses: v })}
                            unit="$"
                        />
                        <InputSlider
                            label="Current Portfolio"
                            value={params.currentPortfolio}
                            min={0}
                            max={2000000}
                            step={5000}
                            onChange={(v: number) => setParams({ ...params, currentPortfolio: v })}
                            unit="$"
                        />
                    </div>

                    <div className="w-full h-px bg-slate-200"></div>

                    <div className="space-y-4">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest pl-1">Assumptions</p>
                        <InputSlider
                            label="Investment Return"
                            value={params.investmentReturn}
                            min={-2}
                            max={15}
                            step={0.5}
                            onChange={(v: number) => setParams({ ...params, investmentReturn: v })}
                            unit="%"
                        />
                        <InputSlider
                            label="Expense Inflation"
                            value={params.expenseInflation}
                            min={0}
                            max={10}
                            step={0.5}
                            onChange={(v: number) => setParams({ ...params, expenseInflation: v })}
                            unit="%"
                        />
                        <InputSlider
                            label="Income Growth"
                            value={params.incomeGrowth}
                            min={0}
                            max={20}
                            step={0.5}
                            onChange={(v: number) => setParams({ ...params, incomeGrowth: v })}
                            unit="%"
                        />
                    </div>
                </div>

                {/* Chart */}
                <div className="lg:col-span-8 h-[500px] bg-white rounded-lg p-2">
                    <Chart type='bar' options={options} data={chartData} />
                </div>
            </div>
        </div>
    );
}
