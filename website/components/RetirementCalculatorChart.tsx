'use client';

import { RetirementSeriesPoint } from '@/lib/retirementCalculator';

interface Props {
  series: RetirementSeriesPoint[];
  milestoneAge: number;
  milestoneLabel?: string;
}

const WIDTH = 800;
const HEIGHT = 320;
const PADDING = { top: 20, right: 20, bottom: 32, left: 64 };

function axisUnitFor(maxAbsValue: number): { divisor: number; suffix: string } {
  if (maxAbsValue >= 10_000_000) return { divisor: 10_000_000, suffix: 'Cr' };
  if (maxAbsValue >= 100_000) return { divisor: 100_000, suffix: 'L' };
  return { divisor: 1, suffix: '' };
}

export default function RetirementCalculatorChart({ series, milestoneAge, milestoneLabel = 'Retirement' }: Props) {
  if (series.length < 2) return null;

  const ages = series.map((point) => point.age);
  const values = series.map((point) => point.value);
  const minAge = Math.min(...ages);
  const maxAge = Math.max(...ages);
  const minValue = Math.min(0, ...values);
  const maxValue = Math.max(...values, 1);

  const plotWidth = WIDTH - PADDING.left - PADDING.right;
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom;

  const xForAge = (age: number) =>
    PADDING.left + ((age - minAge) / (maxAge - minAge || 1)) * plotWidth;
  const yForValue = (value: number) =>
    PADDING.top + plotHeight - ((value - minValue) / (maxValue - minValue || 1)) * plotHeight;

  const linePath = series
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${xForAge(point.age)} ${yForValue(point.value)}`)
    .join(' ');

  const areaPath = `${linePath} L ${xForAge(maxAge)} ${yForValue(0)} L ${xForAge(minAge)} ${yForValue(0)} Z`;

  const milestoneX = xForAge(milestoneAge);
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((fraction) => minValue + fraction * (maxValue - minValue));
  const axisUnit = axisUnitFor(Math.max(Math.abs(minValue), Math.abs(maxValue)));
  const formatAxisValue = (value: number) =>
    `₹${(value / axisUnit.divisor).toFixed(axisUnit.divisor === 1 ? 0 : 1)}${axisUnit.suffix}`;

  const depletionPoint = series.find((point) => point.age > milestoneAge && point.value <= 0);
  const depletionAge = depletionPoint && depletionPoint.age < maxAge ? depletionPoint.age : null;
  const depletionX = depletionAge !== null ? xForAge(depletionAge) : null;
  const depletionLabelAnchor = depletionX !== null && depletionX > WIDTH - 140 ? 'end' : 'start';
  const depletionLabelX = depletionX !== null ? depletionX + (depletionLabelAnchor === 'end' ? -6 : 6) : 0;

  const xAxisAges = Array.from(
    new Set(depletionAge !== null ? [minAge, milestoneAge, depletionAge, maxAge] : [minAge, milestoneAge, maxAge])
  );

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto" role="img" aria-label="Projected portfolio value by age">
      {yTicks.map((tick) => (
        <g key={tick}>
          <line
            x1={PADDING.left}
            x2={WIDTH - PADDING.right}
            y1={yForValue(tick)}
            y2={yForValue(tick)}
            stroke="#e2e8f0"
            strokeWidth={1}
          />
          <text x={PADDING.left - 8} y={yForValue(tick) + 4} textAnchor="end" fontSize={11} fill="#64748b">
            {formatAxisValue(tick)}
          </text>
        </g>
      ))}

      <line
        x1={milestoneX}
        x2={milestoneX}
        y1={PADDING.top}
        y2={HEIGHT - PADDING.bottom}
        stroke="#f59e0b"
        strokeWidth={2}
        strokeDasharray="4 4"
      />
      <text x={milestoneX + 6} y={PADDING.top + 12} fontSize={11} fill="#b45309">
        {milestoneLabel} (age {milestoneAge})
      </text>

      <path d={areaPath} fill="#0891b2" fillOpacity={0.12} />
      <path d={linePath} fill="none" stroke="#0891b2" strokeWidth={2.5} />

      {depletionX !== null && (
        <>
          <line
            x1={depletionX}
            x2={depletionX}
            y1={PADDING.top}
            y2={HEIGHT - PADDING.bottom}
            stroke="#e11d48"
            strokeWidth={2}
            strokeDasharray="4 4"
          />
          <circle cx={depletionX} cy={yForValue(0)} r={4} fill="#e11d48" />
          <text x={depletionLabelX} y={PADDING.top + 28} textAnchor={depletionLabelAnchor} fontSize={11} fill="#be123c">
            Money runs out (age {depletionAge})
          </text>
        </>
      )}

      {xAxisAges.map((age) => (
        <text key={age} x={xForAge(age)} y={HEIGHT - PADDING.bottom + 20} textAnchor="middle" fontSize={11} fill="#64748b">
          Age {age}
        </text>
      ))}
    </svg>
  );
}
