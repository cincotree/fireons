"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function AuthCallbackPage() {
  const { completeLogin } = useAuth();
  const [error, setError] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const token = new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token");
    window.history.replaceState(null, "", window.location.pathname);
    if (!token) {
      setError("Sign-in did not complete. Please try again.");
      return;
    }
    completeLogin(token)
      .then((ok) => {
        if (!ok) setError("Sign-in did not complete. Please try again.");
      })
      .catch(() => setError("Sign-in did not complete. Please try again."));
  }, [completeLogin]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      {error ? (
        <div className="text-center space-y-3">
          <p role="alert" className="text-sm text-red-800">{error}</p>
          <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500">
            Back to login
          </Link>
        </div>
      ) : (
        <p className="text-lg text-gray-600">Signing you in...</p>
      )}
    </div>
  );
}
