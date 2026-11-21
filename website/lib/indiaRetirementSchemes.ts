import { RetirementSeriesPoint } from './retirementCalculator';

function accumulateAnnually(
  currentAge: number,
  endAge: number,
  startingBalance: number,
  annualContributionForYear: (yearIndex: number) => number,
  annualRatePct: number
): { finalBalance: number; totalContributions: number; series: RetirementSeriesPoint[] } {
  let balance = startingBalance;
  let totalContributions = 0;
  const rate = annualRatePct / 100;
  const series: RetirementSeriesPoint[] = [{ age: currentAge, value: balance }];

  let yearIndex = 0;
  for (let age = currentAge + 1; age <= endAge; age++, yearIndex++) {
    const contribution = annualContributionForYear(yearIndex);
    totalContributions += contribution;
    balance = (balance + contribution) * (1 + rate);
    series.push({ age, value: balance });
  }

  return { finalBalance: balance, totalContributions, series };
}

export interface EpfInputs {
  currentAge: number;
  retirementAge: number;
  currentBalance: number;
  monthlyBasicSalary: number;
  employeeContributionPct: number;
  employerContributionPct: number;
  annualSalaryGrowthPct: number;
  annualInterestRatePct: number;
  fireNumber: number;
}

export interface SchemeResult {
  corpusAtRetirement: number;
  totalContributions: number;
  totalInterestEarned: number;
  series: RetirementSeriesPoint[];
  fireNumberCoveragePct: number | null;
}

export function calculateEpf(inputs: EpfInputs): SchemeResult {
  const combinedPct = (inputs.employeeContributionPct + inputs.employerContributionPct) / 100;
  const salaryGrowth = inputs.annualSalaryGrowthPct / 100;

  const { finalBalance, totalContributions, series } = accumulateAnnually(
    inputs.currentAge,
    inputs.retirementAge,
    inputs.currentBalance,
    (yearIndex) => inputs.monthlyBasicSalary * Math.pow(1 + salaryGrowth, yearIndex) * combinedPct * 12,
    inputs.annualInterestRatePct
  );

  return {
    corpusAtRetirement: finalBalance,
    totalContributions,
    totalInterestEarned: finalBalance - inputs.currentBalance - totalContributions,
    series,
    fireNumberCoveragePct: inputs.fireNumber > 0 ? (finalBalance / inputs.fireNumber) * 100 : null,
  };
}

export const PPF_ANNUAL_CONTRIBUTION_LIMIT = 150000;

export interface PpfInputs {
  currentAge: number;
  retirementAge: number;
  currentBalance: number;
  annualContribution: number;
  annualInterestRatePct: number;
  fireNumber: number;
}

export function calculatePpf(inputs: PpfInputs): SchemeResult {
  const clampedContribution = Math.min(inputs.annualContribution, PPF_ANNUAL_CONTRIBUTION_LIMIT);

  const { finalBalance, totalContributions, series } = accumulateAnnually(
    inputs.currentAge,
    inputs.retirementAge,
    inputs.currentBalance,
    () => clampedContribution,
    inputs.annualInterestRatePct
  );

  return {
    corpusAtRetirement: finalBalance,
    totalContributions,
    totalInterestEarned: finalBalance - inputs.currentBalance - totalContributions,
    series,
    fireNumberCoveragePct: inputs.fireNumber > 0 ? (finalBalance / inputs.fireNumber) * 100 : null,
  };
}

export interface NpsInputs {
  currentAge: number;
  retirementAge: number;
  currentBalance: number;
  monthlyContribution: number;
  expectedReturnPct: number;
  annuityPurchasePct: number;
  annuityRatePct: number;
  fireNumber: number;
}

export interface NpsResult extends SchemeResult {
  lumpsumWithdrawal: number;
  annuityCorpus: number;
  monthlyPension: number;
}

export function calculateNps(inputs: NpsInputs): NpsResult {
  const { finalBalance, totalContributions, series } = accumulateAnnually(
    inputs.currentAge,
    inputs.retirementAge,
    inputs.currentBalance,
    () => inputs.monthlyContribution * 12,
    inputs.expectedReturnPct
  );

  const annuityCorpus = finalBalance * (inputs.annuityPurchasePct / 100);
  const lumpsumWithdrawal = finalBalance - annuityCorpus;
  const monthlyPension = (annuityCorpus * (inputs.annuityRatePct / 100)) / 12;

  return {
    corpusAtRetirement: finalBalance,
    totalContributions,
    totalInterestEarned: finalBalance - inputs.currentBalance - totalContributions,
    series,
    fireNumberCoveragePct: inputs.fireNumber > 0 ? (finalBalance / inputs.fireNumber) * 100 : null,
    lumpsumWithdrawal,
    annuityCorpus,
    monthlyPension,
  };
}
