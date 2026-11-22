"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { clearAdminToken, getAdminToken } from "@/utils/adminToken";

const LINKS = [
  { href: "/admin/jobs", label: "Jobs" },
  { href: "/admin/exchange-rates", label: "Exchange rates" },
];

interface AdminSession {
  signOut: () => void;
}

const AdminSessionContext = createContext<AdminSession | undefined>(undefined);

export function useAdminSession(): AdminSession {
  const session = useContext(AdminSessionContext);
  if (!session) {
    throw new Error("useAdminSession must be used inside AdminShell");
  }
  return session;
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const isLoginPage = pathname.startsWith("/admin/login");

  const signOut = useCallback(() => {
    clearAdminToken();
    setReady(false);
    router.replace("/admin/login");
  }, [router]);

  useEffect(() => {
    if (isLoginPage) {
      return;
    }
    if (getAdminToken()) {
      setReady(true);
    } else {
      router.replace("/admin/login");
    }
  }, [isLoginPage, router]);

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading...</p>
      </div>
    );
  }

  return (
    <AdminSessionContext.Provider value={{ signOut }}>
      <div className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-8 py-3 flex items-center justify-between">
          <nav className="flex items-center gap-6">
            <span className="text-sm font-semibold">Admin</span>
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm ${
                  pathname.startsWith(link.href)
                    ? "text-blue-600 font-medium"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <Button type="button" variant="outline" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </div>
      {children}
    </AdminSessionContext.Provider>
  );
}
