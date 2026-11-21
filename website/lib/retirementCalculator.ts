export type AllocationChoice = 'aggressive' | 'balanced' | 'conservative';

export const ALLOCATION_EQUITY_WEIGHT: Record<AllocationChoice, number> = {
  aggressive: 0.8,
  balanced: 0.6,
  conservative: 0.3,
};

export const ALLOCATION_LABELS: Record<AllocationChoice, string> = {
  aggressive: 'Aggressive (80% equity)',
  balanced: 'Balanced (60% equity)',
  conservative: 'Conservative (30% equity)',
};

export interface RetirementInputs {
  currentAge: number;
  contributionEndAge: number;
  retirementAge: number;
  lifeExpectancy: number;
  monthlyExpenseToday: number;
  currentSavings: number;
  inflationPct: number;
  equityReturnPct: number;
  debtReturnPct: number;
  preRetirementAllocation: AllocationChoice;
  postRetirementAllocation: AllocationChoice;
  stepUpEnabled: boolean;
  stepUpPct: number;
}

export interface RetirementSeriesPoint {
  age: number;
  value: number;
}

export interface RetirementResult {
  requiredMonthlySip: number;
  finalMonthlySip: number;
  corpusAtRetirement: number;
  series: RetirementSeriesPoint[];
  isAlreadyOnTrack: boolean;
}

export interface CoastFireInputs {
  currentAge: number;
  retirementAge: number;
  lifeExpectancy: number;
  monthlyExpenseToday: number;
  currentSavings: number;
  inflationPct: number;
  equityReturnPct: number;
  debtReturnPct: number;
  preRetirementAllocation: AllocationChoice;
  postRetirementAllocation: AllocationChoice;
}

export interface CoastFireResult {
  coastFireNumber: number;
  isAlreadyCoastFire: boolean;
  projectedCorpusAtRetirement: number;
  series: RetirementSeriesPoint[];
}

export interface CityFireInputs {
  currentAge: number;
  retirementAge: number;
  currentSavings: number;
  monthlyExpenseToday: number;
  withdrawalRatePct: number;
  inflationPct: number;
  equityReturnPct: number;
  debtReturnPct: number;
  allocation: AllocationChoice;
}

export interface CityFireResult {
  fireNumberToday: number;
  fireNumberAtRetirement: number;
  requiredMonthlySip: number;
  isAlreadyOnTrack: boolean;
  series: RetirementSeriesPoint[];
}

function blendedAnnualReturn(inputs: RetirementInputs, allocation: AllocationChoice): number {
  const equityWeight = ALLOCATION_EQUITY_WEIGHT[allocation];
  const blendedPct = equityWeight * inputs.equityReturnPct + (1 - equityWeight) * inputs.debtReturnPct;
  return blendedPct / 100;
}

function simulate(inputs: RetirementInputs, monthlySip: number): {
  finalBalance: number;
  corpusAtRetirement: number;
  series: RetirementSeriesPoint[];
  finalMonthlySip: number;
} {
  const preReturn = blendedAnnualReturn(inputs, inputs.preRetirementAllocation);
  const postReturn = blendedAnnualReturn(inputs, inputs.postRetirementAllocation);
  const inflation = inputs.inflationPct / 100;
  const stepUp = inputs.stepUpEnabled ? inputs.stepUpPct / 100 : 0;

  let balance = inputs.currentSavings;
  let currentMonthlySip = monthlySip;
  let finalMonthlySip = monthlySip;
  const series: RetirementSeriesPoint[] = [{ age: inputs.currentAge, value: balance }];

  for (let age = inputs.currentAge + 1; age <= inputs.retirementAge; age++) {
    const isContributing = age <= inputs.contributionEndAge;
    balance = balance * (1 + preReturn) + (isContributing ? currentMonthlySip * 12 : 0);
    series.push({ age, value: balance });
    if (isContributing) {
      finalMonthlySip = currentMonthlySip;
      currentMonthlySip *= 1 + stepUp;
    }
  }

  const corpusAtRetirement = balance;
  const yearsToRetire = inputs.retirementAge - inputs.currentAge;
  let annualWithdrawal = inputs.monthlyExpenseToday * 12 * Math.pow(1 + inflation, yearsToRetire);

  for (let age = inputs.retirementAge + 1; age <= inputs.lifeExpectancy; age++) {
    balance = balance * (1 + postReturn) - annualWithdrawal;
    series.push({ age, value: Math.max(0, balance) });
    annualWithdrawal *= 1 + inflation;
  }

  return { finalBalance: balance, corpusAtRetirement, series, finalMonthlySip };
}

const MAX_MONTHLY_SIP = 10_000_000;
const BINARY_SEARCH_ITERATIONS = 60;

function solveMonthlySipForTargetCorpus(
  inputs: RetirementInputs,
  targetCorpus: number
): { requiredMonthlySip: number; isAlreadyOnTrack: boolean; series: RetirementSeriesPoint[] } {
  const zeroSip = simulate(inputs, 0);
  if (zeroSip.corpusAtRetirement >= targetCorpus) {
    return { requiredMonthlySip: 0, isAlreadyOnTrack: true, series: zeroSip.series };
  }

  let lo = 0;
  let hi = MAX_MONTHLY_SIP;
  for (let i = 0; i < BINARY_SEARCH_ITERATIONS; i++) {
    const mid = (lo + hi) / 2;
    const { corpusAtRetirement } = simulate(inputs, mid);
    if (corpusAtRetirement > targetCorpus) {
      hi = mid;
    } else {
      lo = mid;
    }
  }

  const requiredMonthlySip = (lo + hi) / 2;
  const { series } = simulate(inputs, requiredMonthlySip);
  return { requiredMonthlySip, isAlreadyOnTrack: false, series };
}

export function simulateRetirement(inputs: RetirementInputs): RetirementResult {
  if (simulate(inputs, 0).finalBalance >= 0) {
    const { corpusAtRetirement, series, finalMonthlySip } = simulate(inputs, 0);
    return { requiredMonthlySip: 0, finalMonthlySip, corpusAtRetirement, series, isAlreadyOnTrack: true };
  }

  let lo = 0;
  let hi = MAX_MONTHLY_SIP;
  for (let i = 0; i < BINARY_SEARCH_ITERATIONS; i++) {
    const mid = (lo + hi) / 2;
    const { finalBalance } = simulate(inputs, mid);
    if (finalBalance > 0) {
      hi = mid;
    } else {
      lo = mid;
    }
  }

  const requiredMonthlySip = (lo + hi) / 2;
  const { corpusAtRetirement, series, finalMonthlySip } = simulate(inputs, requiredMonthlySip);
  return { requiredMonthlySip, finalMonthlySip, corpusAtRetirement, series, isAlreadyOnTrack: false };
}

const MAX_COAST_FIRE_SAVINGS = 1_000_000_000;

function toCoastRetirementInputs(inputs: CoastFireInputs, currentSavings: number): RetirementInputs {
  return {
    currentAge: inputs.currentAge,
    contributionEndAge: inputs.currentAge,
    retirementAge: inputs.retirementAge,
    lifeExpectancy: inputs.lifeExpectancy,
    monthlyExpenseToday: inputs.monthlyExpenseToday,
    currentSavings,
    inflationPct: inputs.inflationPct,
    equityReturnPct: inputs.equityReturnPct,
    debtReturnPct: inputs.debtReturnPct,
    preRetirementAllocation: inputs.preRetirementAllocation,
    postRetirementAllocation: inputs.postRetirementAllocation,
    stepUpEnabled: false,
    stepUpPct: 0,
  };
}

export function simulateCoastFire(inputs: CoastFireInputs): CoastFireResult {
  const actual = simulate(toCoastRetirementInputs(inputs, inputs.currentSavings), 0);
  const isAlreadyCoastFire = actual.finalBalance >= 0;

  let lo = 0;
  let hi = MAX_COAST_FIRE_SAVINGS;
  for (let i = 0; i < BINARY_SEARCH_ITERATIONS; i++) {
    const mid = (lo + hi) / 2;
    const { finalBalance } = simulate(toCoastRetirementInputs(inputs, mid), 0);
    if (finalBalance > 0) {
      hi = mid;
    } else {
      lo = mid;
    }
  }
  const coastFireNumber = (lo + hi) / 2;

  return {
    coastFireNumber,
    isAlreadyCoastFire,
    projectedCorpusAtRetirement: actual.corpusAtRetirement,
    series: actual.series,
  };
}

function toCityFireRetirementInputs(inputs: CityFireInputs): RetirementInputs {
  return {
    currentAge: inputs.currentAge,
    contributionEndAge: inputs.retirementAge,
    retirementAge: inputs.retirementAge,
    lifeExpectancy: inputs.retirementAge,
    monthlyExpenseToday: inputs.monthlyExpenseToday,
    currentSavings: inputs.currentSavings,
    inflationPct: inputs.inflationPct,
    equityReturnPct: inputs.equityReturnPct,
    debtReturnPct: inputs.debtReturnPct,
    preRetirementAllocation: inputs.allocation,
    postRetirementAllocation: inputs.allocation,
    stepUpEnabled: false,
    stepUpPct: 0,
  };
}

export function calculateCityFire(inputs: CityFireInputs): CityFireResult {
  const yearsToRetire = inputs.retirementAge - inputs.currentAge;
  const inflation = inputs.inflationPct / 100;
  const withdrawalRate = inputs.withdrawalRatePct / 100;

  const fireNumberToday = (inputs.monthlyExpenseToday * 12) / withdrawalRate;
  const fireNumberAtRetirement = fireNumberToday * Math.pow(1 + inflation, yearsToRetire);

  const retirementInputs = toCityFireRetirementInputs(inputs);
  const { requiredMonthlySip, isAlreadyOnTrack, series } = solveMonthlySipForTargetCorpus(
    retirementInputs,
    fireNumberAtRetirement
  );

  return {
    fireNumberToday,
    fireNumberAtRetirement,
    requiredMonthlySip,
    isAlreadyOnTrack,
    series,
  };
}

export interface ReturnToIndiaInputs {
  currentAge: number;
  returnAge: number;
  currentSavingsUsd: number;
  monthlyExpenseInrToday: number;
  exchangeRateInrPerUsd: number;
  inrDepreciationPct: number;
  withdrawalRatePct: number;
  inflationPct: number;
  usdEquityReturnPct: number;
  usdDebtReturnPct: number;
  allocation: AllocationChoice;
}

export interface ReturnToIndiaResult {
  fireNumberInrToday: number;
  fireNumberInrAtReturn: number;
  fireNumberUsdAtReturn: number;
  exchangeRateAtReturn: number;
  requiredMonthlySipUsd: number;
  isAlreadyOnTrack: boolean;
  series: RetirementSeriesPoint[];
}

function toReturnToIndiaRetirementInputs(inputs: ReturnToIndiaInputs): RetirementInputs {
  return {
    currentAge: inputs.currentAge,
    contributionEndAge: inputs.returnAge,
    retirementAge: inputs.returnAge,
    lifeExpectancy: inputs.returnAge,
    monthlyExpenseToday: 0,
    currentSavings: inputs.currentSavingsUsd,
    inflationPct: inputs.inflationPct,
    equityReturnPct: inputs.usdEquityReturnPct,
    debtReturnPct: inputs.usdDebtReturnPct,
    preRetirementAllocation: inputs.allocation,
    postRetirementAllocation: inputs.allocation,
    stepUpEnabled: false,
    stepUpPct: 0,
  };
}

export function calculateReturnToIndia(inputs: ReturnToIndiaInputs): ReturnToIndiaResult {
  const yearsToReturn = inputs.returnAge - inputs.currentAge;
  const inflation = inputs.inflationPct / 100;
  const depreciation = inputs.inrDepreciationPct / 100;
  const withdrawalRate = inputs.withdrawalRatePct / 100;

  const fireNumberInrToday = (inputs.monthlyExpenseInrToday * 12) / withdrawalRate;
  const fireNumberInrAtReturn = fireNumberInrToday * Math.pow(1 + inflation, yearsToReturn);
  const exchangeRateAtReturn = inputs.exchangeRateInrPerUsd * Math.pow(1 + depreciation, yearsToReturn);
  const fireNumberUsdAtReturn = fireNumberInrAtReturn / exchangeRateAtReturn;

  const retirementInputs = toReturnToIndiaRetirementInputs(inputs);
  const { requiredMonthlySip, isAlreadyOnTrack, series } = solveMonthlySipForTargetCorpus(
    retirementInputs,
    fireNumberUsdAtReturn
  );

  return {
    fireNumberInrToday,
    fireNumberInrAtReturn,
    fireNumberUsdAtReturn,
    exchangeRateAtReturn,
    requiredMonthlySipUsd: requiredMonthlySip,
    isAlreadyOnTrack,
    series,
  };
}
