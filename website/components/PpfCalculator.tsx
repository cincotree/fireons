'use client';

import { useEffect, useMemo } from 'react';
import { PpfInputs, calculatePpf } from '@/lib/indiaRetirementSchemes';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import { decodeParamsToInputs, encodeInputsToParams } from '@/lib/urlState';
import PpfCalculatorForm from './PpfCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';
import ShareButton from './ShareButton';
import EmailResultForm from './EmailResultForm';

export const DEFAULT_INPUTS: PpfInputs = {
  currentAge: 30,
  retirementAge: 50,
  currentBalance: 200000,
  annualContribution: 150000,
  annualInterestRatePct: 7.1,
  fireNumber: 0,
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function PpfCalculator() {
  const [inputs, setInputs] = useLocalStorageState<PpfInputs>('fireons-ppf-calculator', DEFAULT_INPUTS);

  const handleChange = (patch: Partial<PpfInputs>) => {
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
    return calculatePpf(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <PpfCalculatorForm values={inputs} onChange={handleChange} />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Target age must be after your current age.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">PPF corpus at age {inputs.retirementAge}</p>
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
                Your PPF alone covers{' '}
                <span className="font-bold text-cyan-700">{result.fireNumberCoveragePct.toFixed(1)}%</span> of your{' '}
                {formatRupees(inputs.fireNumber)} FIRE number.
              </p>
            </div>
          )}

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.retirementAge} milestoneLabel="Target" />

          <p className="text-xs text-slate-500 text-center">
            Assumes annual compounding at {inputs.annualInterestRatePct}%/yr on a flat ₹
            {Math.round(inputs.annualContribution).toLocaleString('en-IN')}/yr contribution. For guidance on your
            actual plan, consult a financial professional.
          </p>

          <ShareButton
            text={`My PPF alone is projected to grow to ${formatRupees(result.corpusAtRetirement)}. Calculate yours:`}
            buildUrl={() =>
              `${window.location.origin}${window.location.pathname}?${encodeInputsToParams(inputs).toString()}`
            }
          />

          <EmailResultForm
            calculatorTitle="PPF Calculator"
            resultSummary={`Your PPF alone is projected to grow to ${formatRupees(result.corpusAtRetirement)} by age ${inputs.retirementAge} (${formatRupees(result.totalContributions)} contributed, ${formatRupees(result.totalInterestEarned)} in interest).${
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
