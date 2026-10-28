'use client';

import { useEffect, useMemo } from 'react';
import { CityFireInputs, calculateCityFire } from '@/lib/retirementCalculator';
import { citiesByRegion, findCityById, isValidCityId, isValidRegionId } from '@/lib/costOfLiving';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import { decodeParamsToInputs, encodeInputsToParams, isAllocationChoice } from '@/lib/urlState';
import CityFireCalculatorForm from './CityFireCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';
import ShareButton from './ShareButton';

type CityFireFormState = CityFireInputs & { regionId: string; cityId: string };

const DEFAULT_CITY_ID = 'goa';
const DEFAULT_REGION_ID = findCityById(DEFAULT_CITY_ID)!.region;

export const DEFAULT_INPUTS: CityFireFormState = {
  regionId: DEFAULT_REGION_ID,
  cityId: DEFAULT_CITY_ID,
  currentAge: 30,
  retirementAge: 50,
  currentSavings: 2500000,
  monthlyExpenseToday: findCityById(DEFAULT_CITY_ID)!.monthlyExpense,
  withdrawalRatePct: 4,
  inflationPct: 6,
  equityReturnPct: 12,
  debtReturnPct: 7,
  allocation: 'aggressive',
};

function resolveSelection(regionId: string, cityId: string): { regionId: string; cityId: string } {
  const safeRegionId = isValidRegionId(regionId) ? regionId : DEFAULT_REGION_ID;
  const cities = citiesByRegion(safeRegionId);
  const safeCityId = cities.some((city) => city.id === cityId) ? cityId : cities[0]?.id ?? DEFAULT_CITY_ID;
  return { regionId: safeRegionId, cityId: safeCityId };
}

function formatRupees(value: number): string {
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export default function CityFireCalculator() {
  const [inputs, setInputs] = useLocalStorageState<CityFireFormState>(
    'fireons-city-fire-calculator',
    DEFAULT_INPUTS
  );

  const handleChange = (patch: Partial<CityFireInputs>) => {
    setInputs((current) => ({ ...current, ...patch }));
  };

  const handleCityChange = (cityId: string) => {
    const city = findCityById(cityId);
    setInputs((current) => ({
      ...current,
      cityId,
      monthlyExpenseToday: city ? city.monthlyExpense : current.monthlyExpenseToday,
    }));
  };

  const handleRegionChange = (regionId: string) => {
    const firstCity = citiesByRegion(regionId)[0];
    setInputs((current) => ({
      ...current,
      regionId,
      cityId: firstCity ? firstCity.id : current.cityId,
      monthlyExpenseToday: firstCity ? firstCity.monthlyExpense : current.monthlyExpenseToday,
    }));
  };

  useEffect(() => {
    const decoded = decodeParamsToInputs(new URLSearchParams(window.location.search), DEFAULT_INPUTS, {
      allocation: isAllocationChoice,
      regionId: isValidRegionId,
      cityId: isValidCityId,
    });
    if (decoded) {
      setInputs(decoded);
    }
  }, [setInputs]);

  const { regionId: safeRegionId, cityId: safeCityId } = useMemo(
    () => resolveSelection(inputs.regionId, inputs.cityId),
    [inputs.regionId, inputs.cityId]
  );

  const cityName = useMemo(() => {
    if (safeCityId === 'other') return 'your village';
    return findCityById(safeCityId)?.name ?? 'your city';
  }, [safeCityId]);

  const result = useMemo(() => {
    if (inputs.retirementAge <= inputs.currentAge || inputs.withdrawalRatePct <= 0) {
      return null;
    }
    return calculateCityFire(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <CityFireCalculatorForm
        regionId={safeRegionId}
        cityId={safeCityId}
        values={inputs}
        onRegionChange={handleRegionChange}
        onCityChange={handleCityChange}
        onChange={handleChange}
      />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          Your target FIRE age must be after your current age, and the withdrawal rate must be greater than zero.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Your FIRE number in {cityName} today</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">{formatRupees(result.fireNumberToday)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Inflation-adjusted at age {inputs.retirementAge}</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.fireNumberAtRetirement)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">
                {result.isAlreadyOnTrack ? 'You are already on track' : 'Invest starting now'}
              </p>
              <p className="text-3xl sm:text-4xl font-bold text-cyan-700">
                {result.isAlreadyOnTrack ? '₹0/mo' : `${formatRupees(result.requiredMonthlySip)}/mo`}
              </p>
            </div>
          </div>

          <RetirementCalculatorChart series={result.series} milestoneAge={inputs.retirementAge} milestoneLabel="FIRE" />

          <p className="text-xs text-slate-500 text-center">
            The {safeCityId === 'other' ? 'monthly expense' : `${cityName} cost-of-living`} figure is an illustrative
            average, not a verified survey — edit it to match your own spending. Assumes a flat monthly investment,
            a {inputs.withdrawalRatePct}% withdrawal rate in retirement, and the return/allocation assumptions above.
            For guidance on your actual plan, consult a financial professional.
          </p>

          <ShareButton
            text={
              result.isAlreadyOnTrack
                ? `My FIRE number in ${cityName} is ${formatRupees(result.fireNumberAtRetirement)}, and I'm already on track! Calculate your own FIRE number:`
                : `My FIRE number in ${cityName} is ${formatRupees(result.fireNumberAtRetirement)}. I need to invest ${formatRupees(result.requiredMonthlySip)}/mo to get there. Calculate your own FIRE number:`
            }
            buildUrl={() =>
              `${window.location.origin}${window.location.pathname}?${encodeInputsToParams(inputs).toString()}`
            }
          />
        </div>
      )}
    </div>
  );
}
