'use client';

import { ALLOCATION_LABELS, AllocationChoice } from '@/lib/retirementCalculator';

export const inputClass =
  'w-full px-4 py-3 rounded-lg border-2 border-slate-300 text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 transition-all';
export const numberInputClass =
  'w-full pl-4 pr-24 py-3 rounded-lg border-2 border-slate-300 text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 transition-all';
export const labelClass = 'block text-sm font-medium text-slate-700 mb-1';

const allocationOptions: AllocationChoice[] = ['aggressive', 'balanced', 'conservative'];

export function NumberField({
  label,
  suffix,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  suffix?: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <div className="relative">
        <input
          type="number"
          className={numberInputClass}
          value={Number.isFinite(value) ? value : ''}
          min={min}
          max={max}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        {suffix && (
          <span className="absolute right-10 top-1/2 -translate-y-1/2 text-slate-400 text-sm pointer-events-none">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

export function AllocationField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: AllocationChoice;
  onChange: (value: AllocationChoice) => void;
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <select
        className={inputClass}
        value={value}
        onChange={(event) => onChange(event.target.value as AllocationChoice)}
      >
        {allocationOptions.map((option) => (
          <option key={option} value={option}>
            {ALLOCATION_LABELS[option]}
          </option>
        ))}
      </select>
    </div>
  );
}
