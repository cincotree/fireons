"use client";

import { useEffect, useState } from "react";
import { getBaseHttpUrl } from "@/utils/api";

const PROVIDERS = [
  { key: "google", label: "Continue with Google" },
  { key: "reddit", label: "Continue with Reddit" },
] as const;

const ERROR_MESSAGES: Record<string, string> = {
  state_invalid: "That sign-in attempt expired or was not valid. Please try again.",
  provider_denied: "Sign-in was cancelled.",
  provider_failed: "We could not complete sign-in with that provider. Please try again.",
  invite_required: "New accounts need an invite code. Create your account on the registration page with your invite code.",
  email_unverified: "That email is already registered and the provider has not verified it. Log in with your password instead.",
};

export function oauthErrorMessage(code: string): string {
  return ERROR_MESSAGES[code] ?? "Sign-in failed. Please try again.";
}

export type AuthProviders = Record<string, boolean>;

export function useAuthProviders(): AuthProviders | null {
  const [providers, setProviders] = useState<AuthProviders | null>(null);

  useEffect(() => {
    fetch(`${getBaseHttpUrl()}/api/auth/providers`)
      .then((response) => (response.ok ? response.json() : {}))
      .then(setProviders)
      .catch(() => setProviders({}));
  }, []);

  return providers;
}

export function OAuthButtons({ inviteCode = "", providers }: { inviteCode?: string; providers: AuthProviders | null }) {
  const enabled = providers ?? {};
  const available = PROVIDERS.filter((provider) => enabled[provider.key]);
  if (available.length === 0) {
    return null;
  }

  const query = inviteCode ? `?invite_code=${encodeURIComponent(inviteCode)}` : "";

  return (
    <div className="mt-6">
      {enabled.password && (
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-gray-50 px-2 text-gray-500">Or</span>
          </div>
        </div>
      )}
      <div className="grid gap-3">
        {available.map((provider) => (
          <a
            key={provider.key}
            href={`${getBaseHttpUrl()}/api/auth/${provider.key}/login${query}`}
            className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {provider.label}
          </a>
        ))}
      </div>
    </div>
  );
}
