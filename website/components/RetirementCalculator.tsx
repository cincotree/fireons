'use client';

import { useMemo } from 'react';
import { RetirementInputs, simulateRetirement } from '@/lib/retirementCalculator';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import RetirementCalculatorForm from './RetirementCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';

const DEFAULT_INPUTS: RetirementInputs = {
  currentAge: 30,
  contributionEndAge: 55,
  retirementAge: 55,
  lifeExpectancy: 85,
  monthlyExpenseToday: 75000,
  currentSavings: 2500000,
  inflationPct: 6,
  equityReturnPct: 12,
  debtReturnPct: 7,
  preRetirementAllocation: 'aggressive',
  postRetirementAllocation: 'conservative',
  stepUpEnabled: false,
  stepUpPct: 5,
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function RetirementCalculator() {
  const [inputs, setInputs] = useLocalStorageState<RetirementInputs>(
    'fireons-retirement-calculator',
    DEFAULT_INPUTS
  );

  const handleChange = (patch: Partial<RetirementInputs>) => {
    setInputs((current) => ({ ...current, ...patch }));
  };

  const result = useMemo(() => {
    if (
      inputs.retirementAge <= inputs.currentAge ||
      inputs.lifeExpectancy < inputs.retirementAge ||
      inputs.contributionEndAge <= inputs.currentAge
    ) {
      return null;
    }
    return simulateRetirement(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <RetirementCalculatorForm values={inputs} onChange={handleChange} />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Retirement age must be after your current age, the age you stop investing must be after your current age,
          and your money should last at least until you retire.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-center">
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">
                {result.isAlreadyOnTrack ? 'You are already on track' : 'Invest starting now'}
              </p>
              <p className="text-3xl sm:text-4xl font-bold text-cyan-700">
                {result.isAlreadyOnTrack ? '₹0/mo' : `${formatRupees(result.requiredMonthlySip)}/mo`}
              </p>
              {!result.isAlreadyOnTrack && inputs.stepUpEnabled && (
                <p className="text-sm text-slate-500 mt-1">
                  Rising {inputs.stepUpPct}%/yr to {formatRupees(result.finalMonthlySip)}/mo by retirement
                </p>
              )}
              {!result.isAlreadyOnTrack && inputs.contributionEndAge < inputs.retirementAge && (
                <p className="text-sm text-slate-500 mt-1">
                  Until age {inputs.contributionEndAge}, then let it grow until retirement at age{' '}
                  {inputs.retirementAge}
                </p>
              )}
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">
                {result.isAlreadyOnTrack ? 'Projected corpus at retirement' : 'Corpus needed at retirement'}
              </p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.corpusAtRetirement)}
              </p>
            </div>
          </div>

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.retirementAge} />

          <p className="text-xs text-slate-500 text-center">
            Assumes {inputs.stepUpEnabled ? `a ${inputs.stepUpPct}% annual step-up in your investment` : 'a flat monthly investment'},
            inflation-adjusted withdrawals in retirement, and the return/allocation assumptions above. For guidance
            on your actual plan, consult a financial professional.
          </p>
        </div>
      )}
    </div>
  );
}
