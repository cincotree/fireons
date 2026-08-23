export interface CurrencyOption {
  code: string;
  label: string;
  symbol: string;
  color: string;
}

export const SUPPORTED_CURRENCIES: CurrencyOption[] = [
  { code: "INR", label: "INR - Indian Rupee", symbol: "₹", color: "#f97316" },
  { code: "USD", label: "USD - US Dollar", symbol: "$", color: "#22c55e" },
  { code: "EUR", label: "EUR - Euro", symbol: "€", color: "#3b82f6" },
  { code: "GBP", label: "GBP - British Pound", symbol: "£", color: "#a855f7" },
  { code: "JPY", label: "JPY - Japanese Yen", symbol: "¥", color: "#eab308" },
  { code: "CAD", label: "CAD - Canadian Dollar", symbol: "$", color: "#06b6d4" },
  { code: "AUD", label: "AUD - Australian Dollar", symbol: "$", color: "#ec4899" },
];

export function getCurrencySymbol(currencyCode: string): string {
  return SUPPORTED_CURRENCIES.find((c) => c.code === currencyCode)?.symbol ?? currencyCode;
}

export function getCurrencyColor(currencyCode: string): string {
  return SUPPORTED_CURRENCIES.find((c) => c.code === currencyCode)?.color ?? "#6b7280";
}
