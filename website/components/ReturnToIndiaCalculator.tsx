'use client';

import { useEffect, useMemo } from 'react';
import { ReturnToIndiaInputs, calculateReturnToIndia } from '@/lib/retirementCalculator';
import { citiesByRegion, findCityById, isValidCityId, isValidRegionId } from '@/lib/costOfLiving';
import { useLocalStorageState } from '@/lib/useLocalStorageState';
import { decodeParamsToInputs, encodeInputsToParams, isAllocationChoice } from '@/lib/urlState';
import { fetchUsdToInrRate } from '@/lib/exchangeRate';
import ReturnToIndiaCalculatorForm from './ReturnToIndiaCalculatorForm';
import RetirementCalculatorChart from './RetirementCalculatorChart';
import ShareButton from './ShareButton';
import EmailResultForm from './EmailResultForm';

type ReturnToIndiaFormState = ReturnToIndiaInputs & {
  regionId: string;
  cityId: string;
  exchangeRateIsCustom: boolean;
  exchangeRateAsOf: string | null;
};

const DEFAULT_CITY_ID = 'goa';
const DEFAULT_REGION_ID = findCityById(DEFAULT_CITY_ID)!.region;

export const DEFAULT_INPUTS: ReturnToIndiaFormState = {
  regionId: DEFAULT_REGION_ID,
  cityId: DEFAULT_CITY_ID,
  currentAge: 30,
  returnAge: 50,
  currentSavingsUsd: 100000,
  monthlyExpenseInrToday: findCityById(DEFAULT_CITY_ID)!.monthlyExpense,
  exchangeRateInrPerUsd: 83,
  inrDepreciationPct: 3,
  withdrawalRatePct: 4,
  inflationPct: 6,
  usdEquityReturnPct: 9,
  usdDebtReturnPct: 4.5,
  allocation: 'aggressive',
  exchangeRateIsCustom: false,
  exchangeRateAsOf: null,
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

function formatDollars(value: number): string {
  return `$${Math.round(value).toLocaleString('en-US')}`;
}

export default function ReturnToIndiaCalculator() {
  const [inputs, setInputs] = useLocalStorageState<ReturnToIndiaFormState>(
    'fireons-return-to-india-calculator',
    DEFAULT_INPUTS
  );

  const handleChange = (patch: Partial<ReturnToIndiaInputs>) => {
    setInputs((current) => ({
      ...current,
      ...patch,
      ...('exchangeRateInrPerUsd' in patch ? { exchangeRateIsCustom: true, exchangeRateAsOf: null } : {}),
    }));
  };

  const handleCityChange = (cityId: string) => {
    const city = findCityById(cityId);
    setInputs((current) => ({
      ...current,
      cityId,
      monthlyExpenseInrToday: city ? city.monthlyExpense : current.monthlyExpenseInrToday,
    }));
  };

  const handleRegionChange = (regionId: string) => {
    const firstCity = citiesByRegion(regionId)[0];
    setInputs((current) => ({
      ...current,
      regionId,
      cityId: firstCity ? firstCity.id : current.cityId,
      monthlyExpenseInrToday: firstCity ? firstCity.monthlyExpense : current.monthlyExpenseInrToday,
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

  useEffect(() => {
    let cancelled = false;
    fetchUsdToInrRate().then((live) => {
      if (cancelled || !live) return;
      setInputs((current) =>
        current.exchangeRateIsCustom
          ? current
          : { ...current, exchangeRateInrPerUsd: live.rate, exchangeRateAsOf: live.asOf }
      );
    });
    return () => {
      cancelled = true;
    };
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
    if (
      inputs.returnAge <= inputs.currentAge ||
      inputs.withdrawalRatePct <= 0 ||
      inputs.exchangeRateInrPerUsd <= 0
    ) {
      return null;
    }
    return calculateReturnToIndia(inputs);
  }, [inputs]);

  return (
    <div className="space-y-8">
      <ReturnToIndiaCalculatorForm
        regionId={safeRegionId}
        cityId={safeCityId}
        values={inputs}
        exchangeRateAsOf={inputs.exchangeRateAsOf}
        onRegionChange={handleRegionChange}
        onCityChange={handleCityChange}
        onChange={handleChange}
      />

      {!result && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-6 text-center">
          The age you return to India must be after your current age, and the withdrawal rate and exchange rate must
          be greater than zero.
        </div>
      )}

      {result && (
        <div className="bg-cyan-50 rounded-2xl p-8 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">Your FIRE number in {cityName} today</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.fireNumberInrToday)}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">At age {inputs.returnAge} (₹ and $ equivalent)</p>
              <p className="text-3xl sm:text-4xl font-bold text-slate-900">
                {formatRupees(result.fireNumberInrAtReturn)}
              </p>
              <p className="text-sm text-slate-500 mt-1">≈ {formatDollars(result.fireNumberUsdAtReturn)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600 mb-1">
                {result.isAlreadyOnTrack ? 'You are already on track' : 'Invest starting now'}
              </p>
              <p className="text-3xl sm:text-4xl font-bold text-cyan-700">
                {result.isAlreadyOnTrack ? '$0/mo' : `${formatDollars(result.requiredMonthlySipUsd)}/mo`}
              </p>
            </div>
          </div>

          <RetirementCalculatorChart
            series={result.series}
            milestoneAge={inputs.returnAge}
            milestoneLabel="Return to India"
            currency="usd"
          />

          <p className="text-xs text-slate-500 text-center">
            The {safeCityId === 'other' ? 'monthly expense' : `${cityName} cost-of-living`} figure is an illustrative
            average, not a verified survey — edit it to match your own spending. Assumes the rupee depreciates against
            the dollar at {inputs.inrDepreciationPct}%/yr (projected rate at return: {formatRupees(result.exchangeRateAtReturn)}
            /$1), a {inputs.withdrawalRatePct}% withdrawal rate in retirement, and the return/allocation assumptions
            above. For guidance on your actual plan, consult a financial professional.
          </p>

          <ShareButton
            text={
              result.isAlreadyOnTrack
                ? `My Return to India FIRE number for ${cityName} is ${formatRupees(result.fireNumberInrAtReturn)}, and I'm already on track! Calculate your own:`
                : `My Return to India FIRE number for ${cityName} is ${formatRupees(result.fireNumberInrAtReturn)}. I need to invest ${formatDollars(result.requiredMonthlySipUsd)}/mo to get there. Calculate your own:`
            }
            buildUrl={() =>
              `${window.location.origin}${window.location.pathname}?${encodeInputsToParams(inputs).toString()}`
            }
          />

          <EmailResultForm
            calculatorTitle="Return to India (NRI FIRE) Calculator"
            resultSummary={
              result.isAlreadyOnTrack
                ? `Your Return to India FIRE number for ${cityName} is ${formatRupees(result.fireNumberInrAtReturn)} (≈ ${formatDollars(result.fireNumberUsdAtReturn)}) at age ${inputs.returnAge}, and you're already on track!`
                : `Your Return to India FIRE number for ${cityName} is ${formatRupees(result.fireNumberInrAtReturn)} (≈ ${formatDollars(result.fireNumberUsdAtReturn)}) at age ${inputs.returnAge}. Invest ${formatDollars(result.requiredMonthlySipUsd)}/mo to get there.`
            }
          />
        </div>
      )}
    </div>
  );
}
