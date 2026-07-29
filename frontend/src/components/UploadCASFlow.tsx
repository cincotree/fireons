"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/modal";
import { getBaseHttpUrl } from "@/utils/api";

interface CASHoldingPreview {
  amc: string;
  scheme_name: string;
  folio_number: string;
  isin: string | null;
  units: number;
  nav: number;
  market_value: number;
  valuation_date: string;
  source: string | null;
  suggested_account_name: string;
  existing_account_id: string | null;
  warnings: string[];
}

interface CASParseResponse {
  statement_date: string;
  holdings: CASHoldingPreview[];
  warnings: string[];
}

interface HoldingRow {
  selected: boolean;
  amc: string;
  folio_number: string;
  scheme_name: string;
  isin: string | null;
  units: number;
  nav: number;
  market_value: string;
  valuation_date: string;
  currency: string;
  source: string | null;
  original_suggested_account_name: string;
  existing_account_id: string | null;
  warnings: string[];
}

interface UploadCASFlowProps {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

const SOURCES = ["CAMS", "KFintech", "MFCentral", "Not sure"];

function sanitizeComponent(value: string): string {
  return value.trim().replace(/\s+/g, " ").replace(/:/g, "-");
}

function suggestedAccountName(amc: string, folioNumber: string, schemeName: string): string {
  return (
    `Assets:Investment:MutualFund:${sanitizeComponent(amc)}:` +
    `${sanitizeComponent(folioNumber)}:${sanitizeComponent(schemeName)}`
  );
}

export function UploadCASFlow({ open, onClose, onImported }: UploadCASFlowProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [source, setSource] = useState("Not sure");
  const [isParsing, setIsParsing] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documentWarnings, setDocumentWarnings] = useState<string[]>([]);
  const [rows, setRows] = useState<HoldingRow[]>([]);
  const [resultSummary, setResultSummary] = useState<string | null>(null);
  const [importSucceeded, setImportSucceeded] = useState(false);

  const reset = () => {
    setStep(1);
    setFile(null);
    setPassword("");
    setSource("Not sure");
    setError(null);
    setDocumentWarnings([]);
    setRows([]);
    setResultSummary(null);
    setImportSucceeded(false);
  };

  const handleClose = () => {
    const shouldRefresh = importSucceeded;
    reset();
    onClose();
    if (shouldRefresh) {
      onImported();
    }
  };

  const handleParse = async () => {
    if (!file) {
      setError("Please choose a CAS PDF to upload.");
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
      formData.append("source", source);

      const response = await fetch(`${baseUrl}/api/statements/cas/parse`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to parse CAS statement");
      }

      const result = data as CASParseResponse;
      setDocumentWarnings(result.warnings);
      setRows(
        result.holdings.map((h) => ({
          selected: h.units > 0,
          amc: h.amc,
          folio_number: h.folio_number,
          scheme_name: h.scheme_name,
          isin: h.isin,
          units: h.units,
          nav: h.nav,
          market_value: h.market_value.toString(),
          valuation_date: h.valuation_date,
          currency: "INR",
          source: h.source,
          original_suggested_account_name: h.suggested_account_name,
          existing_account_id: h.existing_account_id,
          warnings: h.warnings,
        }))
      );
      setStep(2);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsParsing(false);
    }
  };

  const updateRow = (index: number, patch: Partial<HoldingRow>) => {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  const handleConfirm = async () => {
    const selectedRows = rows.filter((r) => r.selected);
    if (selectedRows.length === 0) {
      setError("Please select at least one holding to import.");
      return;
    }

    setError(null);
    setIsConfirming(true);
    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      const response = await fetch(`${baseUrl}/api/statements/cas/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          holdings: selectedRows.map((row) => ({
            amc: row.amc,
            scheme_name: row.scheme_name,
            folio_number: row.folio_number,
            isin: row.isin,
            units: row.units,
            nav: row.nav,
            market_value: parseFloat(row.market_value),
            valuation_date: row.valuation_date,
            account_name: suggestedAccountName(row.amc, row.folio_number, row.scheme_name),
            currency: row.currency,
            source: row.source,
          })),
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to import holdings");
      }

      setResultSummary(`Created ${data.created_count}, updated ${data.updated_count}`);
      setImportSucceeded(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsConfirming(false);
    }
  };

  const selectedCount = rows.filter((r) => r.selected).length;
  const selectedTotal = rows
    .filter((r) => r.selected)
    .reduce((sum, r) => sum + (parseFloat(r.market_value) || 0), 0);

  return (
    <Modal
      open={open}
      size="wide"
      onOpenChange={(next) => {
        if (!next) handleClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Mutual Fund CAS</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm mb-3">
            {error}
          </div>
        )}

        {step === 1 && (
          <div className="py-2 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">CAS PDF *</label>
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

            <div>
              <label className="block text-sm font-medium mb-1">Source</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                {SOURCES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="py-2 space-y-4">
            {documentWarnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 px-3 py-2 rounded text-sm space-y-1">
                {documentWarnings.map((warning) => (
                  <p key={warning}>{warning}</p>
                ))}
              </div>
            )}

            {resultSummary ? (
              <div className="bg-green-50 border border-green-300 text-green-800 px-3 py-2 rounded text-sm">
                {resultSummary}
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="border-b text-left text-gray-600">
                        <th className="py-2 pr-2"></th>
                        <th className="py-2 pr-2">AMC</th>
                        <th className="py-2 pr-2">Folio</th>
                        <th className="py-2 pr-2">Scheme</th>
                        <th className="py-2 pr-2 text-right">Units</th>
                        <th className="py-2 pr-2 text-right">NAV</th>
                        <th className="py-2 pr-2 text-right">Market Value</th>
                        <th className="py-2 pr-2">Valuation Date</th>
                        <th className="py-2 pr-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, index) => {
                        const accountName = suggestedAccountName(
                          row.amc,
                          row.folio_number,
                          row.scheme_name
                        );
                        const willUpdate =
                          row.existing_account_id !== null &&
                          accountName === row.original_suggested_account_name;

                        return (
                          <tr key={index} className="border-b last:border-0">
                            <td className="py-2 pr-2">
                              <input
                                type="checkbox"
                                checked={row.selected}
                                onChange={(e) =>
                                  updateRow(index, { selected: e.target.checked })
                                }
                              />
                            </td>
                            <td className="py-2 pr-2 whitespace-nowrap">{row.amc}</td>
                            <td className="py-2 pr-2 whitespace-nowrap">{row.folio_number}</td>
                            <td className="py-2 pr-2">
                              <input
                                type="text"
                                className="w-full border rounded px-2 py-1"
                                value={row.scheme_name}
                                onChange={(e) =>
                                  updateRow(index, { scheme_name: e.target.value })
                                }
                              />
                            </td>
                            <td className="py-2 pr-2 text-right whitespace-nowrap">
                              {row.units}
                            </td>
                            <td className="py-2 pr-2 text-right whitespace-nowrap">{row.nav}</td>
                            <td className="py-2 pr-2 text-right">
                              <input
                                type="number"
                                step="0.01"
                                className="w-28 border rounded px-2 py-1 text-right"
                                value={row.market_value}
                                onChange={(e) =>
                                  updateRow(index, { market_value: e.target.value })
                                }
                              />
                            </td>
                            <td className="py-2 pr-2">
                              <input
                                type="date"
                                className="border rounded px-2 py-1"
                                value={row.valuation_date}
                                onChange={(e) =>
                                  updateRow(index, { valuation_date: e.target.value })
                                }
                              />
                            </td>
                            <td className="py-2 pr-2 whitespace-nowrap">
                              {willUpdate ? (
                                <span className="text-blue-700 text-xs">
                                  Will update: {row.original_suggested_account_name.split(":").pop()}
                                </span>
                              ) : (
                                <span className="text-green-700 text-xs">New account</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="text-sm text-gray-600">
                  {selectedCount} of {rows.length} selected · Total ₹
                  {selectedTotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </div>
              </>
            )}
          </div>
        )}

        <DialogFooter>
          <div className="flex gap-3 justify-end w-full">
            <Button variant="outline" onClick={handleClose}>
              {resultSummary ? "Close" : "Cancel"}
            </Button>
            {!resultSummary && (
              step === 1 ? (
                <Button
                  onClick={handleParse}
                  disabled={isParsing}
                  className="bg-gray-200 text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
                >
                  {isParsing ? "Parsing..." : "Parse CAS"}
                </Button>
              ) : (
                <Button
                  onClick={handleConfirm}
                  disabled={isConfirming}
                  className="bg-gray-200 text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
                >
                  {isConfirming ? "Importing..." : `Import ${selectedCount} Holdings`}
                </Button>
              )
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Modal>
  );
}
