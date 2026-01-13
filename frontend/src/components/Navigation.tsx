"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function Navigation() {
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <nav className="bg-gray-800 p-3">
      <div className="flex items-center justify-between">
        <div className="flex gap-8">
          <Link
            href="/"
            className={`text-xl font-bold ${pathname === "/" ? "text-white" : "text-gray-400 hover:text-white"
              }`}
          >
            🤖 AI Money
          </Link>
          <Link
            href="/networth"
            className={`text-xl font-bold ${pathname === "/networth" ? "text-white" : "text-gray-400 hover:text-white"
              }`}
          >
            💰 Net Worth
          </Link>
        </div>

        {isAuthenticated && user && (
          <div className="flex items-center gap-4">
            <span className="text-gray-300 text-sm">
              Welcome, <span className="font-semibold text-white">{user.full_name || user.username}</span>
            </span>
            <button
              onClick={logout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md transition-colors"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
