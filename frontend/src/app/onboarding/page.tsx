"use client";

import { NetWorthConsentGate } from "@/components/NetWorthConsentGate";
import { RequireAuth } from "@/components/RequireAuth";
import { StatementImportFlow } from "@/components/StatementImportFlow";

export default function OnboardingPage() {
  return (
    <RequireAuth>
      <NetWorthConsentGate>
        <StatementImportFlow />
      </NetWorthConsentGate>
    </RequireAuth>
  );
}
