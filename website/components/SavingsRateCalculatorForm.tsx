'use client';

import { SavingsRateInputs } from '@/lib/savingsRateCalculator';
import { NumberField } from './CalculatorFormFields';

interface Props {
  values: SavingsRateInputs;
  onChange: (patch: Partial<SavingsRateInputs>) => void;
}

export default function SavingsRateCalculatorForm({ values, onChange }: Props) {
  return (
    <div className="bg-white p-8 rounded-2xl shadow-md border border-slate-100 space-y-6">
      <NumberField
        label="Current age"
        suffix="years"
        value={values.currentAge}
        min={1}
        onChange={(currentAge) => onChange({ currentAge })}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Monthly take-home income"
          suffix="₹/mo"
          value={values.monthlyIncome}
          min={0}
          onChange={(monthlyIncome) => onChange({ monthlyIncome })}
        />
        <NumberField
          label="Monthly expenses"
          suffix="₹/mo"
          value={values.monthlyExpenses}
          min={0}
          onChange={(monthlyExpenses) => onChange({ monthlyExpenses })}
        />
      </div>

      <NumberField
        label="Current investments"
        suffix="₹"
        value={values.currentSavings}
        min={0}
        onChange={(currentSavings) => onChange({ currentSavings })}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Expected annual return"
          suffix="%"
          value={values.returnPct}
          min={0}
          onChange={(returnPct) => onChange({ returnPct })}
        />
        <NumberField
          label="Expected inflation"
          suffix="%"
          value={values.inflationPct}
          min={0}
          onChange={(inflationPct) => onChange({ inflationPct })}
        />
      </div>
    </div>
  );
}
