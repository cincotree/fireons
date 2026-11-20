"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { NetWorthNotice } from "@/components/NetWorthNotice";
import { ConsentStatus, fetchConsent, grantConsent } from "@/utils/consent";

export function NetWorthConsentGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<ConsentStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setStatus(await fetchConsent());
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Could not load your consent status");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const agree = async () => {
    if (!status) return;
    setSaving(true);
    setSaveError(null);
    try {
      setStatus(await grantConsent(status.notice_version));
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Could not save your consent");
      setAgreed(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  if (loadError) {
    return (
      <div className="max-w-xl mx-auto mt-16 px-6 text-center">
        <p className="text-red-600">{loadError}</p>
        <Button className="mt-4" onClick={load}>
          Try again
        </Button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-lg text-gray-600">Loading...</p>
      </div>
    );
  }

  if (status.granted) {
    return <>{children}</>;
  }

  return (
    <div className="max-w-2xl mx-auto my-10 px-6" data-testid="consent-gate">
      <h1 className="text-2xl font-bold text-gray-900">Your net worth data and how Fireons uses it</h1>
      <p className="mt-2 text-sm text-gray-600">
        Fireons needs your permission before it collects and processes the financial information
        below. Other parts of Fireons, like finding a professional, work without it.
      </p>

      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-5 max-h-[50vh] overflow-y-auto">
        <NetWorthNotice version={status.notice_version} />
      </div>

      <label className="mt-6 flex items-start gap-3 text-sm text-gray-800">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4"
          checked={agreed}
          onChange={(event) => setAgreed(event.target.checked)}
        />
        <span>
          I agree that Fireons may collect and process the financial information and documents I
          provide, as described above, to calculate and show my net worth. I am 18 or over, and the
          documents I upload are mine or I am allowed to share them.
        </span>
      </label>

      {saveError && (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {saveError}
        </p>
      )}

      <Button className="mt-4" disabled={!agreed || saving} onClick={agree}>
        {saving ? "Saving..." : "I agree and continue"}
      </Button>
    </div>
  );
}
