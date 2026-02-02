"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

type AccountType = "Assets" | "Liabilities";

interface Category {
  slug: string;
  label: string;
}

const ASSET_CATEGORIES: Category[] = [
  { slug: "cash", label: "Cash & Checking" },
  { slug: "savings", label: "Savings" },
  { slug: "retirement", label: "Retirement Accounts" },
  { slug: "investment", label: "Investment & Brokerage" },
  { slug: "deposit", label: "Fixed Deposits" },
  { slug: "real_estate", label: "Real Estate" },
  { slug: "vehicle", label: "Vehicles" },
  { slug: "crypto", label: "Cryptocurrency" },
  { slug: "other", label: "Other Assets" },
];

const LIABILITY_CATEGORIES: Category[] = [
  { slug: "credit_card", label: "Credit Cards" },
  { slug: "loan", label: "Loans" },
  { slug: "mortgage", label: "Mortgage" },
  { slug: "other", label: "Other Debt" },
];

interface AddAccountFlowProps {
  onComplete: (accountName: string, currency: string, description: string) => void;
  onCancel: () => void;
}

export function AddAccountFlow({ onComplete, onCancel }: AddAccountFlowProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [accountType, setAccountType] = useState<AccountType | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [accountName, setAccountName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [description, setDescription] = useState("");

  const handleTypeSelect = (type: AccountType) => {
    setAccountType(type);
    setStep(2);
  };

  const handleCategorySelect = (cat: string) => {
    setCategory(cat);
    setStep(3);
  };

  const handleBack = () => {
    if (step === 3) setStep(2);
    else if (step === 2) setStep(1);
  };

  const handleCreate = () => {
    if (!accountType || !category || !accountName.trim()) return;

    const fullAccountName = `${accountType}:${category}:${accountName.trim()}`;
    onComplete(fullAccountName, currency, description);
  };

  const getPreview = () => {
    if (!accountType || !category || !accountName.trim()) return "";
    return `${accountType}:${category}:${accountName.trim()}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-6">
        <div className={`flex items-center gap-2 ${step >= 1 ? 'text-blue-600' : 'text-gray-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
            1
          </div>
          <span className="text-sm font-medium">Type</span>
        </div>
        <div className={`h-0.5 w-12 ${step >= 2 ? 'bg-blue-600' : 'bg-gray-200'}`}></div>
        <div className={`flex items-center gap-2 ${step >= 2 ? 'text-blue-600' : 'text-gray-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
            2
          </div>
          <span className="text-sm font-medium">Category</span>
        </div>
        <div className={`h-0.5 w-12 ${step >= 3 ? 'bg-blue-600' : 'bg-gray-200'}`}></div>
        <div className={`flex items-center gap-2 ${step >= 3 ? 'text-blue-600' : 'text-gray-400'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 3 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
            3
          </div>
          <span className="text-sm font-medium">Details</span>
        </div>
      </div>

      {step === 1 && (
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => handleTypeSelect("Assets")}
            className="p-6 border-2 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-center"
          >
            <div className="text-4xl mb-2">💰</div>
            <div className="font-semibold text-lg">Assets</div>
          </button>
          <button
            onClick={() => handleTypeSelect("Liabilities")}
            className="p-6 border-2 rounded-lg hover:border-red-500 hover:bg-red-50 transition-all text-center"
          >
            <div className="text-4xl mb-2">💳</div>
            <div className="font-semibold text-lg">Liabilities</div>
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto">
          {(accountType === "Assets" ? ASSET_CATEGORIES : LIABILITY_CATEGORIES).map((cat) => (
            <button
              key={cat.slug}
              onClick={() => handleCategorySelect(cat.slug)}
              className="p-4 border rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left"
            >
              <div className="font-medium">{cat.label}</div>
            </button>
          ))}
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Account Name *</label>
            <input
              type="text"
              placeholder="e.g., Chase Freedom, Vanguard 401k"
              className="w-full border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Currency</label>
            <select
              className="w-full border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              <option value="USD">USD - US Dollar</option>
              <option value="INR">INR - Indian Rupee</option>
              <option value="EUR">EUR - Euro</option>
              <option value="GBP">GBP - British Pound</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Description (Optional)
            </label>
            <textarea
              className="w-full border rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={2}
              placeholder="Add notes about this account..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {getPreview() && (
            <div className="bg-gray-50 rounded-lg p-3 border">
              <div className="text-xs text-gray-500 mb-1">Account Path:</div>
              <div className="font-mono text-sm">{getPreview()}</div>
            </div>
          )}
        </div>
      )}

      <div className="flex justify-between pt-4 border-t">
        <div>
          {step > 1 && (
            <Button variant="outline" onClick={handleBack}>
              Back
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          {step === 3 && (
            <Button
              onClick={handleCreate}
              disabled={!accountName.trim()}
            >
              Create Account
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
