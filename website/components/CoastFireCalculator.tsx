'use client';

import { useMemo } from 'react';
import { CoastFireInputs, simulateCoastFire } from '@/lib/retirementCalculator';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import CoastFireCalculatorForm from './CoastFireCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';

const DEFAULT_INPUTS: CoastFireInputs = {
  currentAge: 30,
  retirementAge: 55,
  lifeExpectancy: 85,
  monthlyExpenseToday: 75000,
  currentSavings: 2500000,
  inflationPct: 6,
  equityReturnPct: 12,
  debtReturnPct: 7,
  preRetirementAllocation: 'aggressive',
  postRetirementAllocation: 'conservative',
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function CoastFireCalculator() {
  const [inputs, setInputs] = useLocalStorageState<CoastFireInputs>(
    'fireons-coast-fire-calculator',
    DEFAULT_INPUTS
  );

  const handleChange = (patch: Partial<CoastFireInputs>) => {
    setInputs((current) => ({ ...current, ...patch }));
  };

  const result = useMemo(() => {
    if (inputs.retirementAge <= inputs.currentAge || inputs.lifeExpectancy < inputs.retirementAge) {
      return null;
    }
    return simulateCoastFire(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <CoastFireCalculatorForm values={inputs} onChange={handleChange} />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Retirement age must be after your current age, and your money should last at least until you retire.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          {result.isAlreadyCoastFire ? (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-600 mb-1">You&apos;re already Coast FIRE 🎉</p>
              <p className="text-4xl sm:text-5xl font-bold text-cyan-700">
                {formatRupees(result.projectedCorpusAtRetirement)}
              </p>
              <p className="text-sm text-slate-500 mt-1">
                projected at retirement with no further contributions — your Coast FIRE number was{' '}
                {formatRupees(result.coastFireNumber)}
              </p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm font-medium text-slate-600 mb-1">You need</p>
              <p className="text-4xl sm:text-5xl font-bold text-rose-600">
                {formatRupees(result.coastFireNumber - inputs.currentSavings)}
              </p>
              <p className="text-sm text-slate-500 mt-1">
                more to reach your Coast FIRE number of {formatRupees(result.coastFireNumber)}
              </p>
            </div>
          )}

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.retirementAge} />

          <p className="text-xs text-slate-500 text-center">
            Assumes no further contributions from today, inflation-adjusted withdrawals in retirement, and the
            return/allocation assumptions above. For guidance on your actual plan, consult a financial professional.
          </p>
        </div>
      )}
    </div>
  );
}
