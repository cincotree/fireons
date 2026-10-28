'use client';

import { CityFireInputs } from '@/lib/retirementCalculator';
import { citiesByRegion } from '@/lib/costOfLiving';
import { AllocationField, CitySelectField, NumberField, RegionSelectField } from './CalculatorFormFields';

interface Props {
  regionId: string;
  cityId: string;
  values: CityFireInputs;
  onRegionChange: (regionId: string) => void;
  onCityChange: (cityId: string) => void;
  onChange: (patch: Partial<CityFireInputs>) => void;
}

export default function CityFireCalculatorForm({
  regionId,
  cityId,
  values,
  onRegionChange,
  onCityChange,
  onChange,
}: Props) {
  const cities = citiesByRegion(regionId);

  return (
    <div className="bg-white p-8 rounded-2xl shadow-md border border-slate-100 space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <RegionSelectField label="Region" value={regionId} onChange={onRegionChange} />
        <CitySelectField label="Where do you plan to retire?" value={cityId} cities={cities} onChange={onCityChange} />
        <NumberField
          label="Monthly expense (today's ₹)"
          suffix="₹/mo"
          value={values.monthlyExpenseToday}
          min={0}
          onChange={(monthlyExpenseToday) => onChange({ monthlyExpenseToday })}
        />
      </div>
      <p className="text-xs text-slate-500">
        We prefill an illustrative average for the city you pick — edit it to match your own spending.
      </p>

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
          value={values.retirementAge}
          min={values.currentAge + 1}
          onChange={(retirementAge) => onChange({ retirementAge })}
        />
        <NumberField
          label="Current savings"
          suffix="₹"
          value={values.currentSavings}
          min={0}
          onChange={(currentSavings) => onChange({ currentSavings })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <NumberField
          label="Withdrawal rate"
          suffix="%/yr"
          value={values.withdrawalRatePct}
          min={1}
          max={10}
          onChange={(withdrawalRatePct) => onChange({ withdrawalRatePct })}
        />
        <AllocationField
          label="Investment mix while building your corpus"
          value={values.allocation}
          onChange={(allocation) => onChange({ allocation })}
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
    </div>
  );
}
