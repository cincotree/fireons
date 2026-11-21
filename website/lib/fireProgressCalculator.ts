import { RetirementSeriesPoint } from './retirementCalculator';

const MAX_AGE = 100;
const MAX_MONTHLY_SIP = 10_000_000;
const BINARY_SEARCH_ITERATIONS = 60;

function projectSipSeries(
  currentAge: number,
  endAge: number,
  startingBalance: number,
  monthlySip: number,
  returnPct: number
): RetirementSeriesPoint[] {
  const rate = returnPct / 100;
  let balance = startingBalance;
  const series: RetirementSeriesPoint[] = [{ age: currentAge, value: balance }];
  for (let age = currentAge + 1; age <= endAge; age++) {
    balance = balance * (1 + rate) + monthlySip * 12;
    series.push({ age, value: balance });
  }
  return series;
}

function findFireAge(
  baseSeries: RetirementSeriesPoint[],
  fireNumber: number,
  targetAge: number,
  extend: (endAge: number) => RetirementSeriesPoint[]
): { actualFireAge: number | null; series: RetirementSeriesPoint[] } {
  const crossing = baseSeries.find((point) => point.value >= fireNumber);
  if (crossing || targetAge >= MAX_AGE) {
    return { actualFireAge: crossing ? crossing.age : null, series: baseSeries };
  }
  const extended = extend(MAX_AGE);
  const extendedCrossing = extended.find((point) => point.value >= fireNumber);
  if (!extendedCrossing) {
    return { actualFireAge: null, series: extended };
  }
  return {
    actualFireAge: extendedCrossing.age,
    series: extended.filter((point) => point.age <= extendedCrossing.age),
  };
}

export interface SipFireInputs {
  currentAge: number;
  targetAge: number;
  currentSavings: number;
  monthlySip: number;
  expectedReturnPct: number;
  fireNumber: number;
}

export interface SipFireResult {
  corpusAtTargetAge: number;
  isOnTrack: boolean;
  shortfall: number;
  requiredMonthlySip: number;
  actualFireAge: number | null;
  series: RetirementSeriesPoint[];
}

export function calculateSipFire(inputs: SipFireInputs): SipFireResult {
  const baseSeries = projectSipSeries(
    inputs.currentAge,
    inputs.targetAge,
    inputs.currentSavings,
    inputs.monthlySip,
    inputs.expectedReturnPct
  );
  const corpusAtTargetAge = baseSeries[baseSeries.length - 1].value;
  const isOnTrack = corpusAtTargetAge >= inputs.fireNumber;
  const shortfall = isOnTrack ? 0 : inputs.fireNumber - corpusAtTargetAge;

  let requiredMonthlySip = inputs.monthlySip;
  if (!isOnTrack) {
    let lo = inputs.monthlySip;
    let hi = MAX_MONTHLY_SIP;
    for (let i = 0; i < BINARY_SEARCH_ITERATIONS; i++) {
      const mid = (lo + hi) / 2;
      const series = projectSipSeries(inputs.currentAge, inputs.targetAge, inputs.currentSavings, mid, inputs.expectedReturnPct);
      const finalValue = series[series.length - 1].value;
      if (finalValue > inputs.fireNumber) {
        hi = mid;
      } else {
        lo = mid;
      }
    }
    requiredMonthlySip = (lo + hi) / 2;
  }

  const { actualFireAge, series } = findFireAge(baseSeries, inputs.fireNumber, inputs.targetAge, (endAge) =>
    projectSipSeries(inputs.currentAge, endAge, inputs.currentSavings, inputs.monthlySip, inputs.expectedReturnPct)
  );

  return { corpusAtTargetAge, isOnTrack, shortfall, requiredMonthlySip, actualFireAge, series };
}

function projectLumpsumSeries(
  currentAge: number,
  endAge: number,
  lumpsum: number,
  returnPct: number
): RetirementSeriesPoint[] {
  const rate = returnPct / 100;
  let balance = lumpsum;
  const series: RetirementSeriesPoint[] = [{ age: currentAge, value: balance }];
  for (let age = currentAge + 1; age <= endAge; age++) {
    balance = balance * (1 + rate);
    series.push({ age, value: balance });
  }
  return series;
}

export interface LumpsumFireInputs {
  currentAge: number;
  targetAge: number;
  lumpsumAmount: number;
  expectedReturnPct: number;
  fireNumber: number;
}

export interface LumpsumFireResult {
  corpusAtTargetAge: number;
  isOnTrack: boolean;
  shortfall: number;
  requiredLumpsum: number;
  actualFireAge: number | null;
  series: RetirementSeriesPoint[];
}

export function calculateLumpsumFire(inputs: LumpsumFireInputs): LumpsumFireResult {
  const years = inputs.targetAge - inputs.currentAge;
  const rate = inputs.expectedReturnPct / 100;

  const baseSeries = projectLumpsumSeries(inputs.currentAge, inputs.targetAge, inputs.lumpsumAmount, inputs.expectedReturnPct);
  const corpusAtTargetAge = baseSeries[baseSeries.length - 1].value;
  const isOnTrack = corpusAtTargetAge >= inputs.fireNumber;
  const shortfall = isOnTrack ? 0 : inputs.fireNumber - corpusAtTargetAge;
  const requiredLumpsum = inputs.fireNumber / Math.pow(1 + rate, years);

  const { actualFireAge, series } = findFireAge(baseSeries, inputs.fireNumber, inputs.targetAge, (endAge) =>
    projectLumpsumSeries(inputs.currentAge, endAge, inputs.lumpsumAmount, inputs.expectedReturnPct)
  );

  return { corpusAtTargetAge, isOnTrack, shortfall, requiredLumpsum, actualFireAge, series };
}
