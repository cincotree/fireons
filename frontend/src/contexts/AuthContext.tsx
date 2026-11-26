"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authFetch, getBaseHttpUrl, publicFetch, SESSION_EXPIRED_EVENT } from "@/utils/api";
import { takePostLoginPath } from "@/utils/postLoginPath";

interface User {
  id: string;
  email?: string | null;
  username: string;
  full_name?: string;
  location?: string;
  primary_currency: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  completeLogin: (token: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const fetchCurrentUser = () => authFetch(`${getBaseHttpUrl()}/api/auth/me`);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const endSession = () => setUser(null);
    window.addEventListener(SESSION_EXPIRED_EVENT, endSession);
    checkAuth();
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, endSession);
  }, []);

  useEffect(() => {
    if (!user) return;
    const checkOnReturn = () => {
      if (document.visibilityState !== "visible") return;
      fetchCurrentUser().catch((error) => console.error("Auth check failed:", error));
    };
    document.addEventListener("visibilitychange", checkOnReturn);
    return () => document.removeEventListener("visibilitychange", checkOnReturn);
  }, [user]);

  const checkAuth = async () => {
    try {
      if (!localStorage.getItem("token")) {
        return;
      }

      const response = await fetchCurrentUser();
      if (response.ok) {
        setUser(await response.json());
      }
    } catch (error) {
      console.error("Auth check failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const completeLogin = async (token: string) => {
    const baseUrl = getBaseHttpUrl();
    const response = await publicFetch(`${baseUrl}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      return false;
    }
    localStorage.setItem("token", token);
    setUser(await response.json());
    router.replace(takePostLoginPath());
    return true;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    router.push("/login");
  };

  const value = {
    user,
    loading,
    completeLogin,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
