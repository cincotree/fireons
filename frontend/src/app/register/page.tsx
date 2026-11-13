"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getBaseHttpUrl } from "@/utils/api";
import { OAuthButtons, useAuthProviders } from "@/components/OAuthButtons";

export default function RegisterPage() {
  const [inviteRequired, setInviteRequired] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const providers = useAuthProviders();

  useEffect(() => {
    setInviteCode(new URLSearchParams(window.location.search).get("invite") ?? "");
    fetch(`${getBaseHttpUrl()}/api/auth/registration`)
      .then((response) => (response.ok ? response.json() : null))
      .then((info) => setInviteRequired(Boolean(info?.invite_required)))
      .catch(() => setInviteRequired(false));
  }, []);

  const noProviders = providers !== null && !Object.values(providers).some(Boolean);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Join Fireons
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Already a member?{" "}
            <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500">
              Login
            </Link>
          </p>
        </div>
        {inviteRequired && (
          <div>
            <label htmlFor="invite_code" className="block text-sm font-medium text-gray-700">
              Invite code <span className="text-red-500">*</span>
            </label>
            <input
              id="invite_code"
              name="invite_code"
              type="text"
              className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              placeholder="Paste your invite code"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
            />
          </div>
        )}
        {providers === null && <p className="text-center text-sm text-gray-500">Loading...</p>}
        {noProviders && (
          <p className="text-center text-sm text-gray-600">Sign-in is not available right now.</p>
        )}
        <OAuthButtons providers={providers} inviteCode={inviteRequired ? inviteCode.trim() : ""} />
      </div>
    </div>
  );
}
