"use client";

import Link from "next/link";
import { OAuthButtons, useAuthProviders } from "@/components/OAuthButtons";

export default function RegisterPage() {
  const providers = useAuthProviders();

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
        {providers === null && <p className="text-center text-sm text-gray-500">Loading...</p>}
        {noProviders && (
          <p className="text-center text-sm text-gray-600">Sign-in is not available right now.</p>
        )}
        <OAuthButtons providers={providers} />
      </div>
    </div>
  );
}
