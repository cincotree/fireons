"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getBaseHttpUrl } from "@/utils/api";

const POLL_INTERVAL_MS = 2000;

type RunStatus = "pending" | "processing" | "succeeded" | "failed";

interface IngestionRunResponse {
  id: string;
  status: RunStatus;
  file_count: number;
  positions_count: number | null;
  warnings: string[] | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface FileCheckResult {
  filename: string;
  needs_password: boolean;
}

interface StatementImportFlowProps {
  embedded?: boolean;
  onImported?: () => void;
}

export function StatementImportFlow({ embedded = false, onImported }: StatementImportFlowProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [checkResults, setCheckResults] = useState<FileCheckResult[] | null>(null);
  const [passwordByFilename, setPasswordByFilename] = useState<Record<string, string>>({});
  const [isChecking, setIsChecking] = useState(false);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [run, setRun] = useState<IngestionRunResponse | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const addMoreInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const resetToFilePicker = () => {
    setFiles([]);
    setCheckResults(null);
    setPasswordByFilename({});
    setCheckError(null);
    setSubmitError(null);
    setRun(null);
  };

  const checkFiles = async (candidates: File[]): Promise<FileCheckResult[]> => {
    const baseUrl = await getBaseHttpUrl();
    const token = localStorage.getItem("token");

    const formData = new FormData();
    candidates.forEach((file) => formData.append("files", file));

    const response = await fetch(`${baseUrl}/api/ingestion/check`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Could not check files");
    }
    return data.files;
  };

  const handleCheckFiles = async () => {
    if (files.length === 0) {
      setCheckError("Choose at least one statement PDF.");
      return;
    }

    setCheckError(null);
    setIsChecking(true);
    try {
      setCheckResults(await checkFiles(files));
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : "Could not check files");
    } finally {
      setIsChecking(false);
    }
  };

  const handleAddMoreFiles = async (newFiles: File[]) => {
    if (addMoreInputRef.current) {
      addMoreInputRef.current.value = "";
    }
    if (newFiles.length === 0) {
      return;
    }

    const existingNames = new Set(files.map((f) => f.name));
    const duplicateNames = newFiles.filter((f) => existingNames.has(f.name)).map((f) => f.name);
    const uniqueNewFiles = newFiles.filter((f) => !existingNames.has(f.name));

    if (uniqueNewFiles.length === 0) {
      setCheckError(`Already added: ${duplicateNames.join(", ")}`);
      return;
    }

    setCheckError(
      duplicateNames.length > 0 ? `Skipped already-added file(s): ${duplicateNames.join(", ")}` : null,
    );
    setIsChecking(true);
    try {
      const newResults = await checkFiles(uniqueNewFiles);
      setFiles((prev) => [...prev, ...uniqueNewFiles]);
      setCheckResults((prev) => [...(prev ?? []), ...newResults]);
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : "Could not check the new file(s)");
    } finally {
      setIsChecking(false);
    }
  };

  const handleRemoveFile = (filename: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== filename));
    setCheckResults((prev) => (prev ? prev.filter((f) => f.filename !== filename) : prev));
    setPasswordByFilename((prev) => {
      if (!(filename in prev)) {
        return prev;
      }
      const next = { ...prev };
      delete next[filename];
      return next;
    });
  };

  const pollRun = async (runId: string) => {
    const baseUrl = await getBaseHttpUrl();
    const token = localStorage.getItem("token");

    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${baseUrl}/api/ingestion/runs/${runId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data: IngestionRunResponse = await response.json();
        if (!response.ok) {
          throw new Error((data as unknown as { detail?: string }).detail || "Could not check import status");
        }
        setRun(data);
        if (data.status === "succeeded" || data.status === "failed") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        }
      } catch (err) {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        setSubmitError(err instanceof Error ? err.message : "Could not check import status");
      }
    }, POLL_INTERVAL_MS);
  };

  const filesNeedingPassword = checkResults?.filter((f) => f.needs_password) ?? [];
  const missingPasswords = filesNeedingPassword.some(
    (f) => !passwordByFilename[f.filename]?.trim(),
  );
  const hasNoFiles = !checkResults || checkResults.length === 0;

  const handleSubmit = async () => {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      const passwordsPayload: Record<string, string> = {};
      for (const [filename, value] of Object.entries(passwordByFilename)) {
        if (value.trim()) {
          passwordsPayload[filename] = value;
        }
      }
      formData.append("passwords", JSON.stringify(passwordsPayload));

      const response = await fetch(`${baseUrl}/api/ingestion/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Could not start import");
      }

      setRun({
        id: data.run_id,
        status: "pending",
        file_count: files.length,
        positions_count: null,
        warnings: null,
        error_message: null,
        created_at: new Date().toISOString(),
        completed_at: null,
      });
      pollRun(data.run_id);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Could not start import");
    } finally {
      setIsSubmitting(false);
    }
  };

  const isProcessing = run && (run.status === "pending" || run.status === "processing");

  return (
    <div className={embedded ? "space-y-6" : "max-w-3xl mx-auto p-8 space-y-6"}>
      <div>
        <h1 className={embedded ? "text-xl font-semibold" : "text-2xl font-semibold"}>
          Import your statements
        </h1>
        <p className="text-sm text-gray-500">
          Upload as many statement PDFs as you have — bank, mutual fund, retirement, insurance,
          and more. We&apos;ll process them in the background; this can take a little while for a
          large batch.
        </p>
      </div>

      {!checkResults && !run && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-gray-700">Step 1 of 3 — upload</h2>
          <div>
            <label className="block text-sm font-medium mb-1">Statement PDFs</label>
            <input
              type="file"
              accept="application/pdf"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
            {files.length > 0 && (
              <p className="text-xs text-gray-500 mt-1">{files.length} file(s) selected</p>
            )}
          </div>

          {checkError && <p className="text-red-600 text-sm">{checkError}</p>}

          <Button onClick={handleCheckFiles} disabled={isChecking}>
            {isChecking ? "Checking files..." : "Continue"}
          </Button>
        </div>
      )}

      {checkResults && !run && (
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-medium text-gray-700">Step 2 of 3 — passwords</h2>
            <p className="text-xs text-gray-500">
              Enter a password only for the files that need one, remove anything you don&apos;t
              want to import, or add more files below.
            </p>
          </div>

          {checkResults.length === 0 ? (
            <p className="text-sm text-gray-500">
              No files left. Add at least one statement PDF to continue.
            </p>
          ) : (
            <div className="space-y-2">
              {checkResults.map((f) => (
                <div
                  key={f.filename}
                  data-testid={`file-row-${f.filename}`}
                  className="flex items-center gap-3"
                >
                  <span className="text-sm w-56 truncate" title={f.filename}>
                    {f.filename}
                  </span>
                  {f.needs_password ? (
                    <input
                      type="password"
                      placeholder="Password for this file"
                      className="border rounded px-3 py-1.5 text-sm flex-1 max-w-xs"
                      value={passwordByFilename[f.filename] ?? ""}
                      onChange={(e) =>
                        setPasswordByFilename((prev) => ({
                          ...prev,
                          [f.filename]: e.target.value,
                        }))
                      }
                    />
                  ) : (
                    <span className="text-xs text-gray-400 flex-1">no password needed</span>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove ${f.filename}`}
                    title="Remove this file"
                    disabled={isSubmitting}
                    onClick={() => handleRemoveFile(f.filename)}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Upload more</label>
            <input
              ref={addMoreInputRef}
              type="file"
              accept="application/pdf"
              multiple
              disabled={isChecking || isSubmitting}
              onChange={(e) => handleAddMoreFiles(Array.from(e.target.files ?? []))}
            />
          </div>

          {checkError && <p className="text-amber-600 text-sm">{checkError}</p>}
          {submitError && <p className="text-red-600 text-sm">{submitError}</p>}

          <div className="flex gap-3">
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || isChecking || missingPasswords || hasNoFiles}
            >
              {isSubmitting ? "Starting import..." : "Start Import"}
            </Button>
            <Button variant="outline" onClick={resetToFilePicker} disabled={isSubmitting}>
              Change files
            </Button>
          </div>
        </div>
      )}

      {isProcessing && (
        <div className="space-y-2">
          <p className="text-lg">Processing your {run.file_count} document(s)...</p>
          <p className="text-sm text-gray-500">This page will update automatically.</p>
        </div>
      )}

      {run?.status === "succeeded" && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-gray-700">Step 3 of 3 — done</h2>
          <p className="text-lg text-green-700">
            Imported {run.positions_count} position(s) from {run.file_count} document(s).
          </p>
          {run.warnings && run.warnings.length > 0 && (
            <div className="text-sm text-amber-700 bg-amber-50 rounded p-3">
              <p className="font-medium mb-1">Warnings:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {run.warnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          {embedded ? (
            <Button onClick={onImported}>Done</Button>
          ) : (
            <Link href="/networth">
              <Button>Go to your net worth dashboard</Button>
            </Link>
          )}
        </div>
      )}

      {run?.status === "failed" && (
        <div className="space-y-3">
          <p className="text-red-600">
            Import failed: {run.error_message ?? "an unexpected error occurred"}
          </p>
          <Button onClick={resetToFilePicker}>Try again</Button>
        </div>
      )}
    </div>
  );
}
