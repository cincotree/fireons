'use client';

import { PPF_ANNUAL_CONTRIBUTION_LIMIT, PpfInputs } from '@/lib/indiaRetirementSchemes';
import { NumberField } from './CalculatorFormFields';

interface Props {
  values: PpfInputs;
  onChange: (patch: Partial<PpfInputs>) => void;
}

export default function PpfCalculatorForm({ values, onChange }: Props) {
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
          label="Target age"
          suffix="years"
          value={values.retirementAge}
          min={values.currentAge + 1}
          onChange={(retirementAge) => onChange({ retirementAge })}
        />
        <NumberField
          label="Current PPF balance"
          suffix="₹"
          value={values.currentBalance}
          min={0}
          onChange={(currentBalance) => onChange({ currentBalance })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Annual contribution"
          suffix="₹/yr"
          value={values.annualContribution}
          min={0}
          max={PPF_ANNUAL_CONTRIBUTION_LIMIT}
          onChange={(annualContribution) => onChange({ annualContribution })}
        />
        <NumberField
          label="PPF interest rate"
          suffix="%/yr"
          value={values.annualInterestRatePct}
          min={0}
          onChange={(annualInterestRatePct) => onChange({ annualInterestRatePct })}
        />
      </div>
      <p className="text-xs text-slate-500">
        PPF caps contributions at ₹{PPF_ANNUAL_CONTRIBUTION_LIMIT.toLocaleString('en-IN')}/yr and has a 15-year
        lock-in (extendable in 5-year blocks) — this is a simplified projection, not a PPF passbook.
      </p>

      <div className="border-t border-slate-100 pt-6">
        <NumberField
          label="Your FIRE number (optional)"
          suffix="₹"
          value={values.fireNumber}
          min={0}
          onChange={(fireNumber) => onChange({ fireNumber })}
        />
        <p className="text-xs text-slate-500 mt-1">
          Enter your FIRE number to see how much of it your PPF alone covers.
        </p>
      </div>
    </div>
  );
}
