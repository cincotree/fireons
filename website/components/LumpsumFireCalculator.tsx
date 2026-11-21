'use client';

import { useEffect, useMemo } from 'react';
import { LumpsumFireInputs, calculateLumpsumFire } from '@/lib/fireProgressCalculator';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import { decodeParamsToInputs, encodeInputsToParams } from '@/lib/urlState';
import LumpsumFireCalculatorForm from './LumpsumFireCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';
import ShareButton from './ShareButton';
import EmailResultForm from './EmailResultForm';

export const DEFAULT_INPUTS: LumpsumFireInputs = {
  currentAge: 30,
  targetAge: 50,
  lumpsumAmount: 2000000,
  expectedReturnPct: 12,
  fireNumber: 40000000,
};

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function LumpsumFireCalculator() {
  const [inputs, setInputs] = useLocalStorageState<LumpsumFireInputs>(
    'fireons-lumpsum-fire-calculator',
    DEFAULT_INPUTS
  );

  const handleChange = (patch: Partial<LumpsumFireInputs>) => {
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
    return calculateLumpsumFire(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <LumpsumFireCalculatorForm values={inputs} onChange={handleChange} />

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
                {result.isOnTrack ? 'You reach FIRE at age' : "At this lumpsum, you'll reach FIRE at age"}
              </p>
              <p className="text-3xl sm:text-4xl font-bold text-cyan-700">{result.actualFireAge ?? '100+'}</p>
            </div>
          </div>

          {!result.isOnTrack && (
            <div className="bg-white rounded-xl p-4 text-center">
              <p className="text-sm text-slate-600">
                To hit your FIRE number by age {inputs.targetAge}, you&apos;d need to invest{' '}
                <span className="font-bold text-cyan-700">{formatRupees(result.requiredLumpsum)}</span> today instead.
              </p>
            </div>
          )}

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.targetAge} milestoneLabel="Target age" />

          <p className="text-xs text-slate-500 text-center">
            Assumes a one-time {formatRupees(inputs.lumpsumAmount)} investment compounding annually at{' '}
            {inputs.expectedReturnPct}%/yr, with no further contributions. For guidance on your actual plan, consult
            a financial professional.
          </p>

          <ShareButton
            text={
              result.isOnTrack
                ? `My lumpsum has me on track to hit my ${formatRupees(inputs.fireNumber)} FIRE number by age ${inputs.targetAge}! Check your own:`
                : `I'd need to invest ${formatRupees(result.requiredLumpsum)} today to hit my FIRE number by age ${inputs.targetAge}. Check your own:`
            }
            buildUrl={() =>
              `${window.location.origin}${window.location.pathname}?${encodeInputsToParams(inputs).toString()}`
            }
          />

          <EmailResultForm
            calculatorTitle="Lumpsum Calculator for FIRE"
            resultSummary={
              result.isOnTrack
                ? `Your ${formatRupees(inputs.lumpsumAmount)} lumpsum has you on track to hit your ${formatRupees(inputs.fireNumber)} FIRE number by age ${inputs.targetAge}.`
                : `Your ${formatRupees(inputs.lumpsumAmount)} lumpsum projects to ${formatRupees(result.corpusAtTargetAge)} by age ${inputs.targetAge} — a shortfall of ${formatRupees(result.shortfall)} against your ${formatRupees(inputs.fireNumber)} FIRE number. You'd need to invest ${formatRupees(result.requiredLumpsum)} today instead, or at this amount you'll reach FIRE at age ${result.actualFireAge ?? '100+'}.`
            }
          />
        </div>
      )}
    </div>
  );
}
