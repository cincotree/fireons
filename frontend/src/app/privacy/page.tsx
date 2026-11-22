"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { NetWorthNotice } from "@/components/NetWorthNotice";
import { RequireAuth } from "@/components/RequireAuth";
import { ConsentStatus, fetchConsent, withdrawConsent } from "@/utils/consent";

function PrivacyContent() {
  const [status, setStatus] = useState<ConsentStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchConsent()
      .then(setStatus)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load your consent status"));
  }, []);

  const withdraw = async () => {
    setWorking(true);
    setError(null);
    try {
      const result = await withdrawConsent();
      setStatus(result);
      setConfirming(false);
      setMessage(
        `Consent withdrawn. We erased ${result.accounts_deleted} account(s) and ${result.runs_deleted} import record(s).`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not withdraw your consent");
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto my-10 px-6">
      <h1 className="text-2xl font-bold text-gray-900">Privacy</h1>

      <section className="mt-6 rounded-lg border border-gray-200 bg-white p-5" data-testid="consent-status">
        <h2 className="font-semibold text-gray-900">Net worth data</h2>
        {status ? (
          <p className="mt-1 text-sm text-gray-700">
            {status.granted
              ? `You agreed to notice version ${status.accepted_version}.`
              : "You have not given consent, so Fireons holds no net worth data for you."}
          </p>
        ) : null}

        {message && (
          <p role="status" className="mt-3 text-sm text-green-700">
            {message}
          </p>
        )}
        {error && (
          <p role="alert" className="mt-3 text-sm text-red-600">
            {error}
          </p>
        )}

        {status?.granted && !confirming && (
          <Button className="mt-4" variant="destructive" onClick={() => setConfirming(true)}>
            Withdraw consent and delete my net worth data
          </Button>
        )}
        {status?.granted && confirming && (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-gray-800">
              This permanently erases your accounts, balances and import history. It cannot be undone.
            </p>
            <div className="flex gap-2">
              <Button variant="destructive" disabled={working} onClick={withdraw}>
                {working ? "Erasing..." : "Yes, erase everything"}
              </Button>
              <Button variant="outline" disabled={working} onClick={() => setConfirming(false)}>
                Keep my data
              </Button>
            </div>
          </div>
        )}
      </section>

      <section className="mt-8">
        <h2 className="mb-3 font-semibold text-gray-900">What you agreed to</h2>
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <NetWorthNotice version={status?.notice_version ?? "1.0"} />
        </div>
      </section>
    </div>
  );
}

export default function PrivacyPage() {
  return (
    <RequireAuth>
      <PrivacyContent />
    </RequireAuth>
  );
}
