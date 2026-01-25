import { startOfMonth, subMonths, format, addYears } from "date-fns";

export interface FireInputs {
  currentAge: number;
  retirementAge: number;
  annualExpenses: number;
  currentNetWorth: number;
  annualSavings: number;
  expectedReturn: number; // percentage (e.g., 7 for 7%)
  inflationRate: number; // percentage
  safeWithdrawalRate: number; // percentage (typically 4%)
}

export interface FireProjection {
  age: number;
  year: number;
  netWorth: number;
  expenses: number;
  target: number;
  isFi: boolean;
}

export const calculateFireProjection = (inputs: FireInputs): FireProjection[] => {
  const projection: FireProjection[] = [];
  let currentNetWorth = inputs.currentNetWorth;
  let currentExpenses = inputs.annualExpenses;
  const currentYear = new Date().getFullYear();
  const yearsToModel = 50; // Model up to 50 years into the future

  for (let i = 0; i <= yearsToModel; i++) {
    const age = inputs.currentAge + i;
    const year = currentYear + i;

    // Retirement Target (FI Number) = Annual Expenses / Safe Withdrawal Rate
    const target = currentExpenses / (inputs.safeWithdrawalRate / 100);
    const isFi = currentNetWorth >= target;

    projection.push({
      age,
      year,
      netWorth: Math.round(currentNetWorth),
      expenses: Math.round(currentExpenses),
      target: Math.round(target),
      isFi,
    });

    // Advance to next year
    // Growth
    currentNetWorth = currentNetWorth * (1 + inputs.expectedReturn / 100);
    // Add savings (assuming savings also grow with inflation? roughly keeping simple for now)
    currentNetWorth += inputs.annualSavings;

    // Inflation
    currentExpenses = currentExpenses * (1 + inputs.inflationRate / 100);
  }

  return projection;
};

// Mock Data Generators

export const generateHistoricalNetWorth = (months: number = 24) => {
  const data = [];
  const today = new Date();
  let baseValue = 150000; // Starting value
  let volatility = 0.02; // 2% distinct volatility
  let growthTrend = 0.015; // 1.5% monthly growth

  for (let i = months; i >= 0; i--) {
    const date = subMonths(today, i);

    // Random fluctuation
    const randomChange = 1 + (Math.random() * volatility * 2 - volatility);
    // Growth trend
    baseValue = baseValue * (1 + growthTrend) * randomChange;

    data.push({
      date: format(date, "yyyy-MM-dd"), // "2024-01-25"
      value: Math.round(baseValue),
      assets: Math.round(baseValue * 1.2), // Assets are typically higher
      liabilities: Math.round(baseValue * 0.2), // Debt
    });
  }
  return data;
};

// Mock Accounts - Hierarchical (Beancount style)
export const mockAccounts = [
  { id: "1", name: "Assets:US:Vanguard:VTSAX", type: "Investment", balance: 145000.00, currency: "USD" },
  { id: "2", name: "Assets:US:Vanguard:VBTLX", type: "Investment", balance: 45000.00, currency: "USD" },
  { id: "3", name: "Assets:US:Banks:Chase:Checking", type: "Cash", balance: 8430.50, currency: "USD" },
  { id: "4", name: "Assets:US:Banks:Chase:Savings", type: "Cash", balance: 42000.00, currency: "USD" },
  { id: "5", name: "Assets:US:TechStocks:Robinhood:AAPL", type: "Investment", balance: 24500.00, currency: "USD" },
  { id: "6", name: "Assets:US:TechStocks:Robinhood:NVDA", type: "Investment", balance: 12800.00, currency: "USD" },
  { id: "7", name: "Assets:Crypto:ColdStorage:BTC", type: "Crypto", balance: 68000.00, currency: "USD" },
  { id: "8", name: "Assets:Crypto:HotWallet:ETH", type: "Crypto", balance: 3500.00, currency: "USD" },
  { id: "9", name: "Assets:RealEstate:PrimaryHome", type: "Real Estate", balance: 550000.00, currency: "USD" },
  { id: "10", name: "Liabilities:Mortgage:PrimaryHome", type: "Liability", balance: 420000.00, currency: "USD" },
  { id: "11", name: "Liabilities:CreditCards:ChaseSapphire", type: "Liability", balance: 1450.20, currency: "USD" },
  { id: "12", name: "Liabilities:Loans:StudentLoan", type: "Liability", balance: 12000.00, currency: "USD" },
];

export const getAssetAllocation = (accounts: typeof mockAccounts) => {
  const allocation: Record<string, number> = {};

  accounts.forEach(acc => {
    if (acc.type === 'Liability') return; // Skip debt for asset allocation
    allocation[acc.type] = (allocation[acc.type] || 0) + acc.balance;
  });

  return Object.entries(allocation).map(([name, value]) => ({ name, value }));
};
