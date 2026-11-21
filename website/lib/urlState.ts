import type { AllocationChoice } from '@/lib/retirementCalculator';

export function encodeInputsToParams<T extends object>(inputs: T): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(inputs)) {
    params.set(key, String(value));
  }
  return params;
}

export function decodeParamsToInputs<T extends object>(
  params: URLSearchParams,
  defaults: T,
  validators?: Partial<{ [K in keyof T]: (raw: string) => boolean }>
): T | null {
  let matchedCount = 0;
  const result = { ...defaults };
  (Object.keys(defaults) as Array<keyof T & string>).forEach((key) => {
    const raw = params.get(key);
    if (raw === null) return;
    const defaultValue = defaults[key];
    if (typeof defaultValue === 'number') {
      const parsed = Number(raw);
      if (!Number.isFinite(parsed)) return;
      (result as Record<string, unknown>)[key] = parsed;
      matchedCount++;
    } else if (typeof defaultValue === 'boolean') {
      if (raw !== 'true' && raw !== 'false') return;
      (result as Record<string, unknown>)[key] = raw === 'true';
      matchedCount++;
    } else if (typeof defaultValue === 'string') {
      const validator = validators?.[key];
      if (validator && !validator(raw)) return;
      (result as Record<string, unknown>)[key] = raw;
      matchedCount++;
    }
  });
  return matchedCount > 0 ? result : null;
}

export const isAllocationChoice = (v: string): v is AllocationChoice =>
  v === 'aggressive' || v === 'balanced' || v === 'conservative';
