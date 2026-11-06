"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { OAuthButtons, oauthErrorMessage, useAuthProviders } from "@/components/OAuthButtons";

export default function LoginPage() {
  const [error, setError] = useState("");
  const providers = useAuthProviders();

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("error");
    if (code) {
      setError(oauthErrorMessage(code));
    }
  }, []);

  const noProviders = providers !== null && !Object.values(providers).some(Boolean);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">Login</h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            New here?{" "}
            <Link href="/register" className="font-medium text-blue-600 hover:text-blue-500">
              Join Fireons
            </Link>
          </p>
        </div>
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <div className="text-sm text-red-800">{error}</div>
          </div>
        )}
        {providers === null && <p className="text-center text-sm text-gray-500">Loading...</p>}
        {noProviders && (
          <p className="text-center text-sm text-gray-600">Sign-in is not available right now.</p>
        )}
        <OAuthButtons providers={providers} />
      </div>
    </div>
  );
}
