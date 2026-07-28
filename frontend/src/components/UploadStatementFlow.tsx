"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/modal";
import { getBaseHttpUrl } from "@/utils/api";

interface ParsedStatement {
  bank: string;
  account_holder_name: string | null;
  account_number: string | null;
  account_number_last4: string | null;
  currency: string;
  closing_balance: number;
  statement_date: string;
  suggested_account_name: string;
  warnings: string[];
}

interface UploadStatementFlowProps {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

const CURRENCIES = ["USD", "INR", "EUR", "GBP"];
const SUPPORTED_BANKS = [{ code: "HDFC", label: "HDFC Bank" }];

export function UploadStatementFlow({ open, onClose, onImported }: UploadStatementFlowProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [bank, setBank] = useState("HDFC");
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [isParsing, setIsParsing] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [warnings, setWarnings] = useState<string[]>([]);
  const [accountName, setAccountName] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [closingBalance, setClosingBalance] = useState("");
  const [statementDate, setStatementDate] = useState("");
  const [accountHolderName, setAccountHolderName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");

  const reset = () => {
    setStep(1);
    setFile(null);
    setPassword("");
    setError(null);
    setWarnings([]);
    setAccountName("");
    setCurrency("INR");
    setClosingBalance("");
    setStatementDate("");
    setAccountHolderName("");
    setAccountNumber("");
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleParse = async () => {
    if (!file) {
      setError("Please choose a PDF statement to upload.");
      return;
    }
    if (!password) {
      setError("Please enter the PDF password.");
      return;
    }

    setError(null);
    setIsParsing(true);
    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      const formData = new FormData();
      formData.append("file", file);
      formData.append("password", password);
      formData.append("bank", bank);

      const response = await fetch(`${baseUrl}/api/statements/parse`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to parse statement");
      }

      const result = data as ParsedStatement;
      setWarnings(result.warnings);
      setAccountName(result.suggested_account_name);
      setCurrency(result.currency);
      setClosingBalance(result.closing_balance.toString());
      setStatementDate(result.statement_date);
      setAccountHolderName(result.account_holder_name || "");
      setAccountNumber(result.account_number || "");
      setStep(2);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsParsing(false);
    }
  };

  const handleConfirm = async () => {
    if (!accountName.trim()) {
      setError("Please enter an account name.");
      return;
    }
    if (!closingBalance || !statementDate) {
      setError("Please enter a closing balance and statement date.");
      return;
    }

    setError(null);
    setIsConfirming(true);
    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      const response = await fetch(`${baseUrl}/api/statements/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          bank,
          account_name: accountName.trim(),
          currency,
          closing_balance: parseFloat(closingBalance),
          statement_date: statementDate,
          account_number: accountNumber || null,
          account_holder_name: accountHolderName || null,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to create account");
      }

      handleClose();
      onImported();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) handleClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Bank Statement</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm mb-3">
            {error}
          </div>
        )}

        {step === 1 && (
          <div className="py-2 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Bank *</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={bank}
                onChange={(e) => setBank(e.target.value)}
              >
                {SUPPORTED_BANKS.map((b) => (
                  <option key={b.code} value={b.code}>
                    {b.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Statement PDF *</label>
              <input
                type="file"
                accept="application/pdf"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">PDF Password *</label>
              <input
                type="password"
                className="w-full border rounded px-3 py-2"
                placeholder="Password used to open the PDF"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="py-2 space-y-4">
            {warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 px-3 py-2 rounded text-sm space-y-1">
                {warnings.map((warning) => (
                  <p key={warning}>{warning}</p>
                ))}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium mb-1">Account Name *</label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2"
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Currency *</label>
                <select
                  className="w-full border rounded px-3 py-2"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                >
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Closing Balance *</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full border rounded px-3 py-2"
                  value={closingBalance}
                  onChange={(e) => setClosingBalance(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Statement Date *</label>
                <input
                  type="date"
                  className="w-full border rounded px-3 py-2"
                  value={statementDate}
                  onChange={(e) => setStatementDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Account Number</label>
                <input
                  type="text"
                  className="w-full border rounded px-3 py-2"
                  value={accountNumber}
                  onChange={(e) => setAccountNumber(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Account Holder Name</label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2"
                value={accountHolderName}
                onChange={(e) => setAccountHolderName(e.target.value)}
              />
            </div>
          </div>
        )}

        <DialogFooter>
          <div className="flex gap-3 justify-end w-full">
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            {step === 1 ? (
              <Button
                onClick={handleParse}
                disabled={isParsing}
                className="bg-gray-200 text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
              >
                {isParsing ? "Parsing..." : "Parse Statement"}
              </Button>
            ) : (
              <Button
                onClick={handleConfirm}
                disabled={isConfirming}
                className="bg-gray-200 text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
              >
                {isConfirming ? "Creating..." : "Create Account"}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Modal>
  );
}
