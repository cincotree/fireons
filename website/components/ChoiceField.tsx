'use client';

import { labelClass } from './CalculatorFormFields';

interface ChoiceOption<T extends string> {
  value: T;
  label: string;
  description?: string;
  group?: string;
}

function ChoiceButton<T extends string>({
  option,
  selected,
  onChange,
}: {
  option: ChoiceOption<T>;
  selected: boolean;
  onChange: (value: T) => void;
}) {
  return (
    <button
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
      {option.description && <span className="block text-sm text-slate-500 mt-0.5">{option.description}</span>}
    </button>
  );
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
  const hasGroups = options.some((option) => option.group);

  if (!hasGroups) {
    return (
      <div>
        <label className={labelClass}>{label}</label>
        <div className="grid grid-cols-1 gap-3">
          {options.map((option) => (
            <ChoiceButton key={option.value} option={option} selected={value === option.value} onChange={onChange} />
          ))}
        </div>
      </div>
    );
  }

  const groups: { name: string; options: ChoiceOption<T>[] }[] = [];
  for (const option of options) {
    const groupName = option.group ?? '';
    const existing = groups.find((g) => g.name === groupName);
    if (existing) {
      existing.options.push(option);
    } else {
      groups.push({ name: groupName, options: [option] });
    }
  }

  return (
    <div>
      <label className={labelClass}>{label}</label>
      <div className="space-y-5">
        {groups.map((group) => (
          <div key={group.name}>
            {group.name && (
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">{group.name}</p>
            )}
            <div className="grid grid-cols-1 gap-3">
              {group.options.map((option) => (
                <ChoiceButton
                  key={option.value}
                  option={option}
                  selected={value === option.value}
                  onChange={onChange}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
