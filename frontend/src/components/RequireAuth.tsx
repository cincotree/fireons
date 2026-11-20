"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { rememberPostLoginPath, useAuth } from "@/contexts/AuthContext";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      rememberPostLoginPath(window.location.pathname);
      router.replace("/login");
    }
  }, [isAuthenticated, loading, router]);

  if (loading || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-lg text-gray-600">Loading...</p>
      </div>
    );
  }

  return <>{children}</>;
}
