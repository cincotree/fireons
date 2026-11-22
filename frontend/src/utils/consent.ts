import { getBaseHttpUrl } from "@/utils/api";

export interface ConsentStatus {
  purpose: string;
  notice_version: string;
  granted: boolean;
  accepted_version: string | null;
  updated_at: string | null;
}

export interface ConsentWithdrawal extends ConsentStatus {
  accounts_deleted: number;
  runs_deleted: number;
}

function headers(): HeadersInit {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

const consentUrl = () => `${getBaseHttpUrl()}/api/consent/net-worth`;

export function guessCountry(): string | null {
  try {
    const region = new Intl.Locale(navigator.language).region;
    return region && region.length === 2 ? region : null;
  } catch {
    return null;
  }
}

export async function fetchConsent(): Promise<ConsentStatus> {
  const response = await fetch(consentUrl(), { headers: headers() });
  if (!response.ok) throw new Error("Could not load your consent status");
  return response.json();
}

export async function grantConsent(noticeVersion: string): Promise<ConsentStatus> {
  const response = await fetch(consentUrl(), {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      notice_version: noticeVersion,
      age_confirmed: true,
      country: guessCountry(),
    }),
  });
  if (response.status === 409) {
    throw new Error("The notice was updated. Please read it again before agreeing.");
  }
  if (!response.ok) throw new Error("Could not save your consent. Please try again.");
  return response.json();
}

export async function withdrawConsent(): Promise<ConsentWithdrawal> {
  const response = await fetch(consentUrl(), { method: "DELETE", headers: headers() });
  if (!response.ok) throw new Error("Could not withdraw your consent. Please try again.");
  return response.json();
}
