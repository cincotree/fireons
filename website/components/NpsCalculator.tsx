'use client';

import { useEffect, useMemo } from 'react';
import { NpsInputs, calculateNps } from '@/lib/indiaRetirementSchemes';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import { decodeParamsToInputs, encodeInputsToParams } from '@/lib/urlState';
import NpsCalculatorForm from './NpsCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';
import ShareButton from './ShareButton';
import EmailResultForm from './EmailResultForm';

export const DEFAULT_INPUTS: NpsInputs = {
  currentAge: 30,
  retirementAge: 60,
  currentBalance: 100000,
  monthlyContribution: 10000,
  expectedReturnPct: 10,
  annuityPurchasePct: 40,
  annuityRatePct: 6,
  fireNumber: 0,
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function NpsCalculator() {
  const [inputs, setInputs] = useLocalStorageState<NpsInputs>('fireons-nps-calculator', DEFAULT_INPUTS);

  const handleChange = (patch: Partial<NpsInputs>) => {
    setInputs((current) => ({ ...current, ...patch }));
  };

  useEffect(() => {
    const decoded = decodeParamsToInputs(new URLSearchParams(window.location.search), DEFAULT_INPUTS);
    if (decoded) {
      setInputs(decoded);
    }
  }, [setInputs]);

  const result = useMemo(() => {
    if (inputs.retirementAge <= inputs.currentAge || inputs.annuityPurchasePct < 40) {
      return null;
    }
    return calculateNps(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <NpsCalculatorForm values={inputs} onChange={handleChange} />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Retirement age must be after your current age, and the annuity purchase must be at least 40% of the
          corpus.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">NPS corpus at retirement</p>
              <p className="text-3xl sm:text-4xl font-bold text-cyan-700">
                {formatRupees(result.corpusAtRetirement)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Tax-free lump sum</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.lumpsumWithdrawal)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Monthly pension (annuity)</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.monthlyPension)}/mo
              </p>
            </div>
          </div>

          {result.fireNumberCoveragePct !== null && (
            <div className="bg-white rounded-xl p-4 text-center">
              <p className="text-sm text-slate-600">
                Your NPS corpus covers{' '}
                <span className="font-bold text-cyan-700">{result.fireNumberCoveragePct.toFixed(1)}%</span> of your{' '}
                {formatRupees(inputs.fireNumber)} FIRE number.
              </p>
            </div>
          )}

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.retirementAge} milestoneLabel="Retirement" />

          <p className="text-xs text-slate-500 text-center">
            Assumes annual compounding at {inputs.expectedReturnPct}%/yr, a {inputs.annuityPurchasePct}% annuity
            purchase at retirement, and a {inputs.annuityRatePct}%/yr annuity payout rate. For guidance on your
            actual plan, consult a financial professional.
          </p>

          <ShareButton
            text={`My NPS alone is projected to grow to ${formatRupees(result.corpusAtRetirement)}, with a ${formatRupees(result.monthlyPension)}/mo pension. Calculate yours:`}
            buildUrl={() =>
              `${window.location.origin}${window.location.pathname}?${encodeInputsToParams(inputs).toString()}`
            }
          />

          <EmailResultForm
            calculatorTitle="NPS Calculator"
            resultSummary={`Your NPS is projected to grow to ${formatRupees(result.corpusAtRetirement)} by age ${inputs.retirementAge}: ${formatRupees(result.lumpsumWithdrawal)} as a tax-free lump sum, plus a ${formatRupees(result.monthlyPension)}/mo pension.${
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
