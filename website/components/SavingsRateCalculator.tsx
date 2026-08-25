'use client';

import { useMemo } from 'react';
import { MAX_YEARS, SavingsRateInputs, simulateSavingsRate } from '@/lib/savingsRateCalculator';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import SavingsRateCalculatorForm from './SavingsRateCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';

const DEFAULT_INPUTS: SavingsRateInputs = {
  currentAge: 30,
  monthlyIncome: 150000,
  monthlyExpenses: 90000,
  currentSavings: 1000000,
  returnPct: 12,
  inflationPct: 6,
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function SavingsRateCalculator() {
  const [inputs, setInputs] = useLocalStorageState<SavingsRateInputs>(
    'fireons-savings-rate-calculator',
    DEFAULT_INPUTS
  );

  const handleChange = (patch: Partial<SavingsRateInputs>) => {
    setInputs((current) => ({ ...current, ...patch }));
  };

  const result = useMemo(() => {
    if (inputs.currentAge <= 0) return null;
    return simulateSavingsRate(inputs);
  }, [inputs]);

  const isNotSaving = result !== null && result.savingsRatePct <= 0;
  const isUnreachable = result !== null && result.yearsToFI === null && !isNotSaving;

  return (
    <div className="space-y-8">
      <SavingsRateCalculatorForm values={inputs} onChange={handleChange} />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Current age must be a positive number.
        </div>
      )}

      {result && (isNotSaving || isUnreachable) && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          {isNotSaving
            ? "Your expenses meet or exceed your income, so you're not currently saving anything — try reducing expenses or increasing income."
            : `At this savings rate, it would take more than ${MAX_YEARS} years to reach financial independence — try increasing your savings rate.`}
        </div>
      )}

      {result && !isNotSaving && !isUnreachable && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          {result.yearsToFI === 0 ? (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-600 mb-1">You are already financially independent 🎉</p>
              <p className="text-4xl sm:text-5xl font-bold text-cyan-700">{formatRupees(inputs.currentSavings)}</p>
              <p className="text-sm text-slate-500 mt-1">
                already at or above your FI number of {formatRupees(result.fiNumber)}
              </p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-600 mb-1">You will reach FI in</p>
              <p className="text-4xl sm:text-5xl font-bold text-cyan-700">
                {result.yearsToFI} {result.yearsToFI === 1 ? 'year' : 'years'}
              </p>
              <p className="text-sm text-slate-500 mt-1">
                at age {result.targetAge} — savings rate {result.savingsRatePct.toFixed(0)}%, FI number{' '}
                {formatRupees(result.fiNumber)}
              </p>
            </div>
          )}

          {result.targetAge !== null && (
            <RetirementCalculatorChart
              series={result.series}
              milestoneAge={result.targetAge}
              milestoneLabel="Financial Independence"
            />
          )}

          <p className="text-xs text-slate-500 text-center">
            Assumes a 4% safe withdrawal rate (25× annual expenses), a constant savings rate, and the return/inflation
            assumptions above. For guidance on your actual plan, consult a financial professional.
          </p>
        </div>
      )}
    </div>
  );
}
