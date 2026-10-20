'use client';

import { RetirementInputs } from '@/lib/retirementCalculator';
import { AllocationField, NumberField } from './CalculatorFormFields';

interface Props {
  values: RetirementInputs;
  onChange: (patch: Partial<RetirementInputs>) => void;
}

export default function RetirementCalculatorForm({ values, onChange }: Props) {
  return (
    <div className="bg-white p-8 rounded-2xl shadow-md border border-slate-100 space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <NumberField
          label="Current age"
          suffix="years"
          value={values.currentAge}
          min={1}
          onChange={(currentAge) => onChange({ currentAge })}
        />
        <NumberField
          label="I will invest until age"
          suffix="years"
          value={values.contributionEndAge}
          min={values.currentAge + 1}
          max={values.retirementAge}
          onChange={(contributionEndAge) => onChange({ contributionEndAge })}
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
          label="Current savings earmarked for retirement"
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
          label="Asset allocation before retiring"
          value={values.preRetirementAllocation}
          onChange={(preRetirementAllocation) => onChange({ preRetirementAllocation })}
        />
        <AllocationField
          label="Asset allocation in retirement"
          value={values.postRetirementAllocation}
          onChange={(postRetirementAllocation) => onChange({ postRetirementAllocation })}
        />
      </div>

      <div className="border-t border-slate-100 pt-6">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer">
          <input
            type="checkbox"
            checked={values.stepUpEnabled}
            onChange={(event) => onChange({ stepUpEnabled: event.target.checked })}
            className="w-4 h-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 accent-cyan-600"
          />
          Increase my monthly investment every year (step-up)
        </label>
        {values.stepUpEnabled && (
          <div className="mt-4 sm:w-1/2 sm:pr-2">
            <NumberField
              label="Annual step-up"
              suffix="%"
              value={values.stepUpPct}
              min={0}
              onChange={(stepUpPct) => onChange({ stepUpPct })}
            />
          </div>
        )}
      </div>
    </div>
  );
}
