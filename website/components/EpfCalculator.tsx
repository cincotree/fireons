'use client';

import { useEffect, useMemo } from 'react';
import { EpfInputs, calculateEpf } from '@/lib/indiaRetirementSchemes';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import { decodeParamsToInputs, encodeInputsToParams } from '@/lib/urlState';
import EpfCalculatorForm from './EpfCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';
import ShareButton from './ShareButton';
import EmailResultForm from './EmailResultForm';

export const DEFAULT_INPUTS: EpfInputs = {
  currentAge: 30,
  retirementAge: 58,
  currentBalance: 500000,
  monthlyBasicSalary: 50000,
  employeeContributionPct: 12,
  employerContributionPct: 12,
  annualSalaryGrowthPct: 8,
  annualInterestRatePct: 8.25,
  fireNumber: 0,
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function EpfCalculator() {
  const [inputs, setInputs] = useLocalStorageState<EpfInputs>('fireons-epf-calculator', DEFAULT_INPUTS);

  const handleChange = (patch: Partial<EpfInputs>) => {
    setInputs((current) => ({ ...current, ...patch }));
  };

  useEffect(() => {
    const decoded = decodeParamsToInputs(new URLSearchParams(window.location.search), DEFAULT_INPUTS);
    if (decoded) {
      setInputs(decoded);
    }
  }, [setInputs]);

  const result = useMemo(() => {
    if (inputs.retirementAge <= inputs.currentAge) {
      return null;
    }
    return calculateEpf(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <EpfCalculatorForm values={inputs} onChange={handleChange} />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Retirement age must be after your current age.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">EPF corpus at retirement</p>
              <p className="text-3xl sm:text-4xl font-bold text-cyan-700">
                {formatRupees(result.corpusAtRetirement)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Total contributions</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.totalContributions)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Interest earned</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.totalInterestEarned)}
              </p>
            </div>
          </div>

          {result.fireNumberCoveragePct !== null && (
            <div className="bg-white rounded-xl p-4 text-center">
              <p className="text-sm text-slate-600">
                Your EPF alone covers{' '}
                <span className="font-bold text-cyan-700">{result.fireNumberCoveragePct.toFixed(1)}%</span> of your{' '}
                {formatRupees(inputs.fireNumber)} FIRE number.
              </p>
            </div>
          )}

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.retirementAge} milestoneLabel="Retirement" />

          <p className="text-xs text-slate-500 text-center">
            Assumes annual compounding at {inputs.annualInterestRatePct}%/yr on contributions growing{' '}
            {inputs.annualSalaryGrowthPct}%/yr with your salary. For guidance on your actual plan, consult a
            financial professional.
          </p>

          <ShareButton
            text={`My EPF alone is projected to grow to ${formatRupees(result.corpusAtRetirement)} by retirement. Calculate yours:`}
            buildUrl={() =>
              `${window.location.origin}${window.location.pathname}?${encodeInputsToParams(inputs).toString()}`
            }
          />

          <EmailResultForm
            calculatorTitle="EPF Calculator"
            resultSummary={`Your EPF alone is projected to grow to ${formatRupees(result.corpusAtRetirement)} by age ${inputs.retirementAge} (${formatRupees(result.totalContributions)} contributed, ${formatRupees(result.totalInterestEarned)} in interest).${
              result.fireNumberCoveragePct !== null
                ? ` That covers ${result.fireNumberCoveragePct.toFixed(1)}% of your ${formatRupees(inputs.fireNumber)} FIRE number.`
                : ''
            }`}
          />
        </div>
      )}
    </div>
  );
}
