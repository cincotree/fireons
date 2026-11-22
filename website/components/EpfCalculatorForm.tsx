'use client';

import { EpfInputs } from '@/lib/indiaRetirementSchemes';
import { NumberField } from './CalculatorFormFields';

interface Props {
  values: EpfInputs;
  onChange: (patch: Partial<EpfInputs>) => void;
}

export default function EpfCalculatorForm({ values, onChange }: Props) {
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
          min={values.currentAge + 1}
          onChange={(retirementAge) => onChange({ retirementAge })}
        />
        <NumberField
          label="Current EPF balance"
          suffix="₹"
          value={values.currentBalance}
          min={0}
          onChange={(currentBalance) => onChange({ currentBalance })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Monthly basic salary"
          suffix="₹/mo"
          value={values.monthlyBasicSalary}
          min={0}
          onChange={(monthlyBasicSalary) => onChange({ monthlyBasicSalary })}
        />
        <NumberField
          label="Annual salary growth"
          suffix="%/yr"
          value={values.annualSalaryGrowthPct}
          min={0}
          onChange={(annualSalaryGrowthPct) => onChange({ annualSalaryGrowthPct })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <NumberField
          label="Employee contribution"
          suffix="%"
          value={values.employeeContributionPct}
          min={0}
          max={100}
          onChange={(employeeContributionPct) => onChange({ employeeContributionPct })}
        />
        <NumberField
          label="Employer contribution"
          suffix="%"
          value={values.employerContributionPct}
          min={0}
          max={100}
          onChange={(employerContributionPct) => onChange({ employerContributionPct })}
        />
        <NumberField
          label="EPF interest rate"
          suffix="%/yr"
          value={values.annualInterestRatePct}
          min={0}
          onChange={(annualInterestRatePct) => onChange({ annualInterestRatePct })}
        />
      </div>
      <p className="text-xs text-slate-500">
        Contribution % is of basic salary, and assumes the full employer share lands in your EPF account — in
        practice part of it is routed to the EPS pension scheme above a wage ceiling. This is a simplified estimate,
        not an EPFO statement.
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
          Enter your FIRE number to see how much of it your EPF alone covers.
        </p>
      </div>
    </div>
  );
}
