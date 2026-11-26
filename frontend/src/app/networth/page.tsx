"use client";

import { NetWorthConsentGate } from "@/components/NetWorthConsentGate";
import { RequireAuth } from "@/components/RequireAuth";
import { NetWorthDashboard } from "@/components/NetWorthDashboard";

export default function NetWorthPage() {
  return (
    <RequireAuth>
      <NetWorthConsentGate>
        <NetWorthDashboard />
      </NetWorthConsentGate>
    </RequireAuth>
  );
}
