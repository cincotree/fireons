const EXCHANGE_RATE_ENDPOINT = 'https://api.frankfurter.dev/v1/latest?base=USD&symbols=INR';

export interface LiveExchangeRate {
  rate: number;
  asOf: string;
}

export async function fetchUsdToInrRate(): Promise<LiveExchangeRate | null> {
  try {
    const response = await fetch(EXCHANGE_RATE_ENDPOINT);
    if (!response.ok) return null;
    const data = await response.json();
    const rate = data?.rates?.INR;
    const asOf = data?.date;
    if (typeof rate !== 'number' || !Number.isFinite(rate) || rate <= 0) return null;
    if (typeof asOf !== 'string') return null;
    return { rate, asOf };
  } catch {
    return null;
  }
}
