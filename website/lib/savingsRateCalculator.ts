export interface SavingsRateInputs {
  currentAge: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  currentSavings: number;
  returnPct: number;
  inflationPct: number;
}

export interface SavingsRateSeriesPoint {
  age: number;
  value: number;
}

export interface SavingsRateResult {
  savingsRatePct: number;
  fiNumber: number;
  yearsToFI: number | null;
  targetAge: number | null;
  series: SavingsRateSeriesPoint[];
}

const FI_MULTIPLE = 25;
export const MAX_YEARS = 80;
const CHART_BUFFER_YEARS = 5;

export function simulateSavingsRate(inputs: SavingsRateInputs): SavingsRateResult {
  const monthlySavings = inputs.monthlyIncome - inputs.monthlyExpenses;
  const savingsRatePct = inputs.monthlyIncome > 0 ? (monthlySavings / inputs.monthlyIncome) * 100 : 0;
  const fiNumber = inputs.monthlyExpenses * 12 * FI_MULTIPLE;
  const realReturn = (1 + inputs.returnPct / 100) / (1 + inputs.inflationPct / 100) - 1;

  let balance = inputs.currentSavings;
  const series: SavingsRateSeriesPoint[] = [{ age: inputs.currentAge, value: balance }];
  let yearsToFI: number | null = balance >= fiNumber ? 0 : null;

  for (let year = 1; year <= MAX_YEARS; year++) {
    balance = balance * (1 + realReturn) + monthlySavings * 12;
    series.push({ age: inputs.currentAge + year, value: balance });
    if (yearsToFI === null && balance >= fiNumber) {
      yearsToFI = year;
    }
  }

  const targetAge = yearsToFI !== null ? inputs.currentAge + yearsToFI : null;
  const chartEndYear = yearsToFI !== null ? Math.min(MAX_YEARS, yearsToFI + CHART_BUFFER_YEARS) : MAX_YEARS;
  const chartEndAge = inputs.currentAge + chartEndYear;
  const truncatedSeries = series.filter((point) => point.age <= chartEndAge);

  return { savingsRatePct, fiNumber, yearsToFI, targetAge, series: truncatedSeries };
}
