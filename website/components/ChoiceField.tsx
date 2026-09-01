'use client';

import { labelClass } from './CalculatorFormFields';

interface ChoiceOption<T extends string> {
  value: T;
  label: string;
  description?: string;
}

export function ChoiceField<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: ChoiceOption<T>[];
  value: T | undefined;
  onChange: (value: T) => void;
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <div className="grid grid-cols-1 gap-3">
        {options.map((option) => {
          const selected = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              aria-pressed={selected}
              className={`text-left px-5 py-4 rounded-xl border-2 transition-all ${
                selected
                  ? 'border-cyan-600 bg-cyan-50 ring-2 ring-cyan-100'
                  : 'border-slate-200 hover:border-cyan-300 hover:bg-slate-50'
              }`}
            >
              <span className="block font-semibold text-slate-900">{option.label}</span>
              {option.description && (
                <span className="block text-sm text-slate-500 mt-0.5">{option.description}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
