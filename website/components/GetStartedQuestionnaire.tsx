'use client';

import { useState } from 'react';
import { AllocationChoice, RetirementInputs, CoastFireInputs } from '@/lib/retirementCalculator';
import { SavingsRateInputs } from '@/lib/savingsRateCalculator';
import { DEFAULT_INPUTS as RETIREMENT_DEFAULTS } from './RetirementCalculator';
import { DEFAULT_INPUTS as COAST_FIRE_DEFAULTS } from './CoastFireCalculator';
import { DEFAULT_INPUTS as SAVINGS_RATE_DEFAULTS } from './SavingsRateCalculator';
import { encodeInputsToParams } from '@/lib/urlState';
import { appRoutes } from '@/lib/config';
import { NumberField } from './CalculatorFormFields';
import { ChoiceField } from './ChoiceField';

type Path = 'savings-rate' | 'retirement' | 'coast-fire';

interface Answers {
  path?: Path;
  currentAge?: number;
  monthlyIncome?: number;
  monthlyExpenses?: number;
  currentSavings?: number;
  retirementAge?: number;
  riskComfort?: AllocationChoice;
}

type NumberKey = Exclude<keyof Answers, 'path' | 'riskComfort'>;

type Question =
  | {
      key: 'path';
      kind: 'choice';
      label: string;
      insight: string;
      options: { value: Path; label: string; description?: string }[];
    }
  | { key: NumberKey; kind: 'number'; label: string; suffix?: string; insight: string; min?: number }
  | {
      key: 'riskComfort';
      kind: 'choice';
      label: string;
      insight: string;
      options: { value: AllocationChoice; label: string; description?: string }[];
    };

const ROUTING_QUESTION: Question = {
  key: 'path',
  kind: 'choice',
  label: "What's on your mind right now?",
  insight:
    'FIRE (Financial Independence, Retire Early) has a few common starting questions — pick the one closest to yours.',
  options: [
    { value: 'savings-rate', label: 'How fast am I moving toward FI?', description: 'Based on your savings rate' },
    { value: 'retirement', label: 'How much do I need to invest monthly?', description: 'To retire on your terms' },
    { value: 'coast-fire', label: 'Have I already saved enough to stop?', description: 'Coast to retirement' },
  ],
};

const AGE_QUESTION: Question = {
  key: 'currentAge',
  kind: 'number',
  label: 'How old are you today?',
  suffix: 'years',
  insight: 'Your current age sets the starting point for every FIRE projection.',
  min: 1,
};

const INCOME_QUESTION: Question = {
  key: 'monthlyIncome',
  kind: 'number',
  label: 'What is your monthly take-home income?',
  suffix: '₹/mo',
  insight: 'Your savings rate — income minus expenses, divided by income — is the single biggest lever in FIRE math.',
  min: 0,
};

const EXPENSES_QUESTION: Question = {
  key: 'monthlyExpenses',
  kind: 'number',
  label: 'What do you spend per month?',
  suffix: '₹/mo',
  insight: 'The 4% rule says you need about 25× your annual expenses invested to sustain them indefinitely.',
  min: 0,
};

const SAVINGS_QUESTION: Question = {
  key: 'currentSavings',
  kind: 'number',
  label: 'How much have you already invested for the future?',
  suffix: '₹',
  insight: "What you've already saved keeps compounding — it reduces how much more you need to add.",
  min: 0,
};

const RETIREMENT_AGE_QUESTION: Question = {
  key: 'retirementAge',
  kind: 'number',
  label: 'At what age would you like to be financially independent?',
  suffix: 'years',
  insight: 'Every extra year you invest is also one fewer year your money has to last — this age drives both sides.',
  min: 1,
};

const RISK_QUESTION: Question = {
  key: 'riskComfort',
  kind: 'choice',
  label: 'How would you invest a lump sum today?',
  insight:
    'Higher equity allocations tend to grow faster over decades but swing more year to year — there is no universally "right" answer.',
  options: [
    { value: 'aggressive', label: 'Mostly stocks', description: 'Higher long-term growth, more ups and downs' },
    { value: 'balanced', label: 'A mix of stocks and bonds', description: 'Smoother ride, moderate growth' },
    { value: 'conservative', label: 'Mostly bonds/fixed income', description: 'Lower growth, steadier value' },
  ],
};

function questionsForPath(path: Path | undefined): Question[] {
  if (path === 'savings-rate') {
    return [ROUTING_QUESTION, AGE_QUESTION, INCOME_QUESTION, EXPENSES_QUESTION, SAVINGS_QUESTION];
  }
  if (path === 'retirement' || path === 'coast-fire') {
    return [
      ROUTING_QUESTION,
      AGE_QUESTION,
      EXPENSES_QUESTION,
      SAVINGS_QUESTION,
      RETIREMENT_AGE_QUESTION,
      RISK_QUESTION,
    ];
  }
  return [ROUTING_QUESTION];
}

function buildDestinationHref(answers: Answers): string | null {
  if (!answers.path) return null;

  if (answers.path === 'savings-rate') {
    const inputs: SavingsRateInputs = {
      ...SAVINGS_RATE_DEFAULTS,
      ...(answers.currentAge !== undefined && { currentAge: answers.currentAge }),
      ...(answers.monthlyIncome !== undefined && { monthlyIncome: answers.monthlyIncome }),
      ...(answers.monthlyExpenses !== undefined && { monthlyExpenses: answers.monthlyExpenses }),
      ...(answers.currentSavings !== undefined && { currentSavings: answers.currentSavings }),
    };
    return `${appRoutes.savingsRateCalculator}?${encodeInputsToParams(inputs).toString()}`;
  }

  const sharedOverrides = {
    ...(answers.currentAge !== undefined && { currentAge: answers.currentAge }),
    ...(answers.monthlyExpenses !== undefined && { monthlyExpenseToday: answers.monthlyExpenses }),
    ...(answers.currentSavings !== undefined && { currentSavings: answers.currentSavings }),
    ...(answers.retirementAge !== undefined && { retirementAge: answers.retirementAge }),
    ...(answers.riskComfort !== undefined && { preRetirementAllocation: answers.riskComfort }),
  };

  if (answers.path === 'retirement') {
    const inputs: RetirementInputs = {
      ...RETIREMENT_DEFAULTS,
      ...sharedOverrides,
      ...(answers.retirementAge !== undefined && { contributionEndAge: answers.retirementAge }),
    };
    return `${appRoutes.retirementCalculator}?${encodeInputsToParams(inputs).toString()}`;
  }

  const inputs: CoastFireInputs = { ...COAST_FIRE_DEFAULTS, ...sharedOverrides };
  return `${appRoutes.coastFireCalculator}?${encodeInputsToParams(inputs).toString()}`;
}

export default function GetStartedQuestionnaire() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [draft, setDraft] = useState<number | undefined>(undefined);

  const questions = questionsForPath(answers.path);
  const isDone = step >= questions.length;
  const question = questions[step];

  const goBack = () => {
    setStep((s) => Math.max(0, s - 1));
    setDraft(undefined);
  };

  const answerAndAdvance = (key: keyof Answers, value: Answers[keyof Answers]) => {
    setAnswers((current) => ({ ...current, [key]: value }));
    setDraft(undefined);
    setStep((s) => s + 1);
  };

  if (isDone) {
    const href = buildDestinationHref(answers);
    const pathLabel =
      answers.path === 'savings-rate' ? 'Savings Rate' : answers.path === 'retirement' ? 'Retirement' : 'Coast FIRE';
    return (
      <div className="max-w-xl mx-auto text-center space-y-6">
        <h2 className="text-2xl font-bold text-slate-900">Here&apos;s where to start</h2>
        <p className="text-slate-600">
          Based on your answers, the {pathLabel} Calculator is the best fit — we&apos;ve pre-filled it with what you
          told us.
        </p>
        {href && (
          <button
            type="button"
            onClick={() => {
              window.location.href = href;
            }}
            className="inline-block bg-cyan-700 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-cyan-800 transition-colors shadow-lg"
          >
            See my results →
          </button>
        )}
        <button type="button" onClick={goBack} className="block mx-auto text-sm text-slate-500 hover:underline">
          ← Back
        </button>
      </div>
    );
  }

  const currentValue = question.key === 'path' ? undefined : answers[question.key];

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <p className="text-sm text-cyan-700 bg-cyan-50 rounded-lg px-4 py-3">{question.insight}</p>

      {question.kind === 'choice' ? (
        <ChoiceField
          label={question.label}
          options={question.options as { value: string; label: string; description?: string }[]}
          value={currentValue as string | undefined}
          onChange={(value) => answerAndAdvance(question.key, value as Answers[typeof question.key])}
        />
      ) : (
        <div className="space-y-4">
          <NumberField
            label={question.label}
            suffix={question.suffix}
            min={question.min}
            value={draft ?? (answers[question.key] as number | undefined) ?? NaN}
            onChange={setDraft}
          />
          <button
            type="button"
            disabled={draft === undefined || !Number.isFinite(draft) || (question.min !== undefined && draft < question.min)}
            onClick={() => answerAndAdvance(question.key, draft as number)}
            className="w-full bg-cyan-700 text-white py-3 rounded-lg font-semibold hover:bg-cyan-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Continue
          </button>
        </div>
      )}

      {step > 0 && (
        <button type="button" onClick={goBack} className="text-sm text-slate-500 hover:underline">
          ← Back
        </button>
      )}
    </div>
  );
}
