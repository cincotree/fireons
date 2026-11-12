"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useAdminSession } from "@/components/AdminShell";
import { adminRequest, UnauthorizedError } from "@/utils/adminApi";

interface ExchangeRate {
  id: string;
  date: string;
  from_currency: string;
  to_currency: string;
  rate: string;
  source: string | null;
  updated_at: string;
}

export function AdminExchangeRates() {
  const { signOut } = useAdminSession();
  const [rates, setRates] = useState<ExchangeRate[]>([]);
  const [fromCurrency, setFromCurrency] = useState("");
  const [toCurrency, setToCurrency] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const latestRequest = useRef(0);

  const load = useCallback(async () => {
    const requestId = ++latestRequest.current;
    const params = new URLSearchParams();
    if (fromCurrency.trim()) params.set("from_currency", fromCurrency.trim());
    if (toCurrency.trim()) params.set("to_currency", toCurrency.trim());
    const query = params.toString() ? `?${params}` : "";
    try {
      const result = await adminRequest<ExchangeRate[]>(`/exchange-rates${query}`);
      if (requestId !== latestRequest.current) return;
      setRates(result);
      setError(null);
    } catch (err) {
      if (requestId !== latestRequest.current) return;
      if (err instanceof UnauthorizedError) {
        signOut();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not load exchange rates");
    } finally {
      setLoaded(true);
    }
  }, [fromCurrency, toCurrency, signOut]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="max-w-5xl mx-auto p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Exchange rates</h1>
        <p className="text-sm text-gray-500">Latest 100 rates, newest first.</p>
      </div>

      <div className="flex items-end gap-3">
        <div>
          <label htmlFor="from-currency" className="block text-sm font-medium mb-1">
            From
          </label>
          <input
            id="from-currency"
            value={fromCurrency}
            onChange={(event) => setFromCurrency(event.target.value)}
            placeholder="USD"
            maxLength={10}
            className="border rounded px-3 py-1.5 text-sm w-24 uppercase"
          />
        </div>
        <div>
          <label htmlFor="to-currency" className="block text-sm font-medium mb-1">
            To
          </label>
          <input
            id="to-currency"
            value={toCurrency}
            onChange={(event) => setToCurrency(event.target.value)}
            placeholder="INR"
            maxLength={10}
            className="border rounded px-3 py-1.5 text-sm w-24 uppercase"
          />
        </div>
        <Button type="button" variant="outline" onClick={load}>
          Refresh
        </Button>
      </div>

      {error && (
        <p role="alert" data-testid="rates-error" className="text-red-600 text-sm">
          {error}
        </p>
      )}

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2 pr-4">Date</th>
            <th className="py-2 pr-4">Pair</th>
            <th className="py-2 pr-4">Rate</th>
            <th className="py-2 pr-4">Source</th>
            <th className="py-2 pr-4">Updated</th>
          </tr>
        </thead>
        <tbody>
          {rates.map((rate) => (
            <tr key={rate.id} data-testid="rate-row" className="border-b">
              <td className="py-2 pr-4">{rate.date}</td>
              <td className="py-2 pr-4">
                {rate.from_currency}/{rate.to_currency}
              </td>
              <td className="py-2 pr-4 font-mono">{Number(rate.rate).toFixed(4)}</td>
              <td className="py-2 pr-4">{rate.source || "-"}</td>
              <td className="py-2 pr-4">{new Date(rate.updated_at).toLocaleString()}</td>
            </tr>
          ))}
          {loaded && rates.length === 0 && !error && (
            <tr>
              <td colSpan={5} className="py-4 text-gray-500">
                No exchange rates found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
