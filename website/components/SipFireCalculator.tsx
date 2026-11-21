'use client';

import { useEffect, useMemo } from 'react';
import { SipFireInputs, calculateSipFire } from '@/lib/fireProgressCalculator';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import { decodeParamsToInputs, encodeInputsToParams } from '@/lib/urlState';
import SipFireCalculatorForm from './SipFireCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';
import ShareButton from './ShareButton';
import EmailResultForm from './EmailResultForm';

export const DEFAULT_INPUTS: SipFireInputs = {
  currentAge: 30,
  targetAge: 50,
  currentSavings: 500000,
  monthlySip: 25000,
  expectedReturnPct: 12,
  fireNumber: 40000000,
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function SipFireCalculator() {
  const [inputs, setInputs] = useLocalStorageState<SipFireInputs>('fireons-sip-fire-calculator', DEFAULT_INPUTS);

  const handleChange = (patch: Partial<SipFireInputs>) => {
    setInputs((current) => ({ ...current, ...patch }));
  };

  useEffect(() => {
    const decoded = decodeParamsToInputs(new URLSearchParams(window.location.search), DEFAULT_INPUTS);
    if (decoded) {
      setInputs(decoded);
    }
  }, [setInputs]);

  const result = useMemo(() => {
    if (inputs.targetAge <= inputs.currentAge || inputs.fireNumber <= 0) {
      return null;
    }
    return calculateSipFire(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <SipFireCalculatorForm values={inputs} onChange={handleChange} />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Target FIRE age must be after your current age, and your FIRE number must be greater than zero.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Corpus at age {inputs.targetAge}</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.corpusAtTargetAge)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">
                {result.isOnTrack ? 'You are on track' : 'Shortfall'}
              </p>
              <p className={`text-3xl sm:text-4xl font-bold ${result.isOnTrack ? 'text-emerald-600' : 'text-rose-600'}`}>
                {result.isOnTrack ? 'Yes' : formatRupees(result.shortfall)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">
                {result.isOnTrack ? 'You reach FIRE at age' : "At this SIP, you'll reach FIRE at age"}
              </p>
              <p className="text-3xl sm:text-4xl font-bold text-cyan-700">
                {result.actualFireAge ?? '100+'}
              </p>
            </div>
          </div>

          {!result.isOnTrack && (
            <div className="bg-white rounded-xl p-4 text-center">
              <p className="text-sm text-slate-600">
                To hit your FIRE number by age {inputs.targetAge}, increase your SIP to{' '}
                <span className="font-bold text-cyan-700">{formatRupees(result.requiredMonthlySip)}/mo</span>.
              </p>
            </div>
          )}

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.targetAge} milestoneLabel="Target age" />

          <p className="text-xs text-slate-500 text-center">
            Assumes a flat {formatRupees(inputs.monthlySip)}/mo SIP compounding annually at{' '}
            {inputs.expectedReturnPct}%/yr. For guidance on your actual plan, consult a financial professional.
          </p>

          <ShareButton
            text={
              result.isOnTrack
                ? `My SIP has me on track to hit my ${formatRupees(inputs.fireNumber)} FIRE number by age ${inputs.targetAge}! Check your own SIP:`
                : `I need to bump my SIP to ${formatRupees(result.requiredMonthlySip)}/mo to hit my FIRE number by age ${inputs.targetAge}. Check your own SIP:`
            }
            buildUrl={() =>
              `${window.location.origin}${window.location.pathname}?${encodeInputsToParams(inputs).toString()}`
            }
          />

          <EmailResultForm
            calculatorTitle="SIP Calculator for FIRE"
            resultSummary={
              result.isOnTrack
                ? `Your ${formatRupees(inputs.monthlySip)}/mo SIP has you on track to hit your ${formatRupees(inputs.fireNumber)} FIRE number by age ${inputs.targetAge}.`
                : `Your ${formatRupees(inputs.monthlySip)}/mo SIP projects to ${formatRupees(result.corpusAtTargetAge)} by age ${inputs.targetAge} — a shortfall of ${formatRupees(result.shortfall)} against your ${formatRupees(inputs.fireNumber)} FIRE number. Bump it to ${formatRupees(result.requiredMonthlySip)}/mo to close the gap, or at your current rate you'll reach FIRE at age ${result.actualFireAge ?? '100+'}.`
            }
          />
        </div>
      )}
    </div>
  );
}
