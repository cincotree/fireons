'use client';

import { LumpsumFireInputs } from '@/lib/fireProgressCalculator';
import { NumberField } from './CalculatorFormFields';

interface Props {
  values: LumpsumFireInputs;
  onChange: (patch: Partial<LumpsumFireInputs>) => void;
}

export default function LumpsumFireCalculatorForm({ values, onChange }: Props) {
  return (
    <div className="bg-white p-8 rounded-2xl shadow-md border border-slate-100 space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <NumberField
          label="Current age"
          suffix="years"
          value={values.currentAge}
          min={1}
          onChange={(currentAge) => onChange({ currentAge })}
        />
        <NumberField
          label="Target FIRE age"
          suffix="years"
          value={values.targetAge}
          min={values.currentAge + 1}
          onChange={(targetAge) => onChange({ targetAge })}
        />
        <NumberField
          label="Lumpsum to invest"
          suffix="₹"
          value={values.lumpsumAmount}
          min={0}
          onChange={(lumpsumAmount) => onChange({ lumpsumAmount })}
        />
      </div>

      <NumberField
        label="Expected annual return"
        suffix="%"
        value={values.expectedReturnPct}
        min={0}
        onChange={(expectedReturnPct) => onChange({ expectedReturnPct })}
      />

      <div className="border-t border-slate-100 pt-6">
        <NumberField
          label="Your FIRE number"
          suffix="₹"
          value={values.fireNumber}
          min={0}
          onChange={(fireNumber) => onChange({ fireNumber })}
        />
        <p className="text-xs text-slate-500 mt-1">
          Don&apos;t know your FIRE number yet? Work it out with the{' '}
          <a href="/calculators/retirement" className="underline hover:text-cyan-700">
            Retirement Calculator
          </a>{' '}
          first.
        </p>
      </div>
    </div>
  );
}
