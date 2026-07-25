"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { User } from "lucide-react";

export default function Navigation() {
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <nav className="bg-gray-800 border-b border-gray-600">
      <div className="max-w-7xl mx-auto px-6 py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <Link
              href="/"
              className="text-lg font-bold text-white hover:text-gray-300 transition-colors mr-8"
            >
              🤖 Fireons
            </Link>
            {isAuthenticated && (
              <Link
                href="/networth"
                className={`px-4 py-1.5 text-sm font-medium transition-all border-b ${
                  pathname === "/networth"
                    ? "text-blue-400 border-blue-400"
                    : "text-gray-300 border-transparent hover:text-white hover:border-gray-500"
                }`}
              >
                Net Worth
              </Link>
            )}
          </div>

          {isAuthenticated && user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                  <User className="h-4 w-4 text-gray-300" />
                </div>
                <span className="text-sm text-gray-300">
                  {user.full_name || user.username}
                </span>
              </div>
              <button
                onClick={logout}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
