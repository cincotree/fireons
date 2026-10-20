'use client';

import { CoastFireInputs } from '@/lib/retirementCalculator';
import { AllocationField, NumberField } from './CalculatorFormFields';

interface Props {
  values: CoastFireInputs;
  onChange: (patch: Partial<CoastFireInputs>) => void;
}

export default function CoastFireCalculatorForm({ values, onChange }: Props) {
  return (
    <div className="bg-white p-8 rounded-2xl shadow-md border border-slate-100 space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
          min={values.currentAge + 1}
          onChange={(retirementAge) => onChange({ retirementAge })}
        />
        <NumberField
          label="Money should last till"
          suffix="years"
          value={values.lifeExpectancy}
          min={values.retirementAge}
          onChange={(lifeExpectancy) => onChange({ lifeExpectancy })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Desired monthly spend in retirement (today's ₹)"
          suffix="₹/mo"
          value={values.monthlyExpenseToday}
          min={0}
          onChange={(monthlyExpenseToday) => onChange({ monthlyExpenseToday })}
        />
        <NumberField
          label="Current savings"
          suffix="₹"
          value={values.currentSavings}
          min={0}
          onChange={(currentSavings) => onChange({ currentSavings })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <NumberField
          label="Expected inflation"
          suffix="%"
          value={values.inflationPct}
          min={0}
          onChange={(inflationPct) => onChange({ inflationPct })}
        />
        <NumberField
          label="Expected equity return"
          suffix="%"
          value={values.equityReturnPct}
          min={0}
          onChange={(equityReturnPct) => onChange({ equityReturnPct })}
        />
        <NumberField
          label="Expected debt return"
          suffix="%"
          value={values.debtReturnPct}
          min={0}
          onChange={(debtReturnPct) => onChange({ debtReturnPct })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <AllocationField
          label="Asset allocation while coasting"
          value={values.preRetirementAllocation}
          onChange={(preRetirementAllocation) => onChange({ preRetirementAllocation })}
        />
        <AllocationField
          label="Asset allocation in retirement"
          value={values.postRetirementAllocation}
          onChange={(postRetirementAllocation) => onChange({ postRetirementAllocation })}
        />
      </div>
    </div>
  );
}
