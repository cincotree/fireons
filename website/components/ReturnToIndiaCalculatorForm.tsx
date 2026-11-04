'use client';

import { ReturnToIndiaInputs } from '@/lib/retirementCalculator';
import { citiesByRegion } from '@/lib/costOfLiving';
import { AllocationField, CitySelectField, NumberField, RegionSelectField } from './CalculatorFormFields';

interface Props {
  regionId: string;
  cityId: string;
  values: ReturnToIndiaInputs;
  exchangeRateAsOf: string | null;
  onRegionChange: (regionId: string) => void;
  onCityChange: (cityId: string) => void;
  onChange: (patch: Partial<ReturnToIndiaInputs>) => void;
}

export default function ReturnToIndiaCalculatorForm({
  regionId,
  cityId,
  values,
  exchangeRateAsOf,
  onRegionChange,
  onCityChange,
  onChange,
}: Props) {
  const cities = citiesByRegion(regionId);

  return (
    <div className="bg-white p-8 rounded-2xl shadow-md border border-slate-100 space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <RegionSelectField label="Region" value={regionId} onChange={onRegionChange} />
        <CitySelectField label="Where in India will you retire?" value={cityId} cities={cities} onChange={onCityChange} />
        <NumberField
          label="Monthly expense (today's ₹)"
          suffix="₹/mo"
          value={values.monthlyExpenseInrToday}
          min={0}
          onChange={(monthlyExpenseInrToday) => onChange({ monthlyExpenseInrToday })}
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
          label="Age you'll return to India"
          suffix="years"
          value={values.returnAge}
          min={values.currentAge + 1}
          onChange={(returnAge) => onChange({ returnAge })}
        />
        <NumberField
          label="Current savings"
          suffix="$"
          value={values.currentSavingsUsd}
          min={0}
          onChange={(currentSavingsUsd) => onChange({ currentSavingsUsd })}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <NumberField
            label="Current exchange rate"
            suffix="₹/$1"
            value={values.exchangeRateInrPerUsd}
            min={1}
            onChange={(exchangeRateInrPerUsd) => onChange({ exchangeRateInrPerUsd })}
          />
          <p className="text-xs text-slate-500 mt-1">
            {exchangeRateAsOf ? `Live rate as of ${exchangeRateAsOf} — edit if you'd rather use your own.` : "Edit to use your own rate."}
          </p>
        </div>
        <NumberField
          label="Expected ₹ depreciation vs $"
          suffix="%/yr"
          value={values.inrDepreciationPct}
          min={0}
          onChange={(inrDepreciationPct) => onChange({ inrDepreciationPct })}
        />
      </div>
      <p className="text-xs text-slate-500">
        The rupee has historically lost value against the dollar over time — this assumes it continues at the rate
        above, compounding the exchange rate between now and when you return.
      </p>

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
          label="India inflation"
          suffix="%"
          value={values.inflationPct}
          min={0}
          onChange={(inflationPct) => onChange({ inflationPct })}
        />
        <NumberField
          label="Expected US equity return"
          suffix="%"
          value={values.usdEquityReturnPct}
          min={0}
          onChange={(usdEquityReturnPct) => onChange({ usdEquityReturnPct })}
        />
        <NumberField
          label="Expected US debt return"
          suffix="%"
          value={values.usdDebtReturnPct}
          min={0}
          onChange={(usdDebtReturnPct) => onChange({ usdDebtReturnPct })}
        />
      </div>
    </div>
  );
}
