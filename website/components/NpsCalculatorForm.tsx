'use client';

import { NpsInputs } from '@/lib/indiaRetirementSchemes';
import { NumberField } from './CalculatorFormFields';

interface Props {
  values: NpsInputs;
  onChange: (patch: Partial<NpsInputs>) => void;
}

export default function NpsCalculatorForm({ values, onChange }: Props) {
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
          label="Retirement age"
          suffix="years"
          value={values.retirementAge}
          min={Math.max(60, values.currentAge + 1)}
          onChange={(retirementAge) => onChange({ retirementAge })}
        />
        <NumberField
          label="Current NPS balance"
          suffix="₹"
          value={values.currentBalance}
          min={0}
          onChange={(currentBalance) => onChange({ currentBalance })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Monthly contribution"
          suffix="₹/mo"
          value={values.monthlyContribution}
          min={0}
          onChange={(monthlyContribution) => onChange({ monthlyContribution })}
        />
        <NumberField
          label="Expected annual return"
          suffix="%"
          value={values.expectedReturnPct}
          min={0}
          onChange={(expectedReturnPct) => onChange({ expectedReturnPct })}
        />
      </div>
      <p className="text-xs text-slate-500">
        NPS normally allows exit at age 60 or later, and a minimum 40% of the corpus must be used to buy an annuity —
        the rest can be withdrawn as a lump sum.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Annuity purchase"
          suffix="% of corpus"
          value={values.annuityPurchasePct}
          min={40}
          max={100}
          onChange={(annuityPurchasePct) => onChange({ annuityPurchasePct })}
        />
        <NumberField
          label="Annuity payout rate"
          suffix="%/yr"
          value={values.annuityRatePct}
          min={0}
          onChange={(annuityRatePct) => onChange({ annuityRatePct })}
        />
      </div>

      <div className="border-t border-slate-100 pt-6">
        <NumberField
          label="Your FIRE number (optional)"
          suffix="₹"
          value={values.fireNumber}
          min={0}
          onChange={(fireNumber) => onChange({ fireNumber })}
        />
        <p className="text-xs text-slate-500 mt-1">
          Enter your FIRE number to see how much of it your NPS corpus covers.
        </p>
      </div>
    </div>
  );
}
