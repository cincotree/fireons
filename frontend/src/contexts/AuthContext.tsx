"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getBaseHttpUrl } from "@/utils/api";

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
  login: (username: string, password: string) => Promise<void>;
  completeLogin: (token: string) => Promise<boolean>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  location?: string;
  primary_currency?: string;
  invite_code?: string;
}

const POST_LOGIN_PATH_KEY = "postLoginPath";

export function rememberPostLoginPath(path: string) {
  try {
    if (path.startsWith("/") && !path.startsWith("//")) {
      sessionStorage.setItem(POST_LOGIN_PATH_KEY, path);
    }
  } catch {
    return;
  }
}

function takePostLoginPath(): string {
  try {
    const path = sessionStorage.getItem(POST_LOGIN_PATH_KEY);
    sessionStorage.removeItem(POST_LOGIN_PATH_KEY);
    if (path && path.startsWith("/") && !path.startsWith("//")) {
      return path;
    }
  } catch {
    return "/networth";
  }
  return "/networth";
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setLoading(false);
        return;
      }

      const baseUrl = getBaseHttpUrl();
      const response = await fetch(`${baseUrl}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        localStorage.removeItem("token");
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      localStorage.removeItem("token");
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    const baseUrl = getBaseHttpUrl();
    const response = await fetch(`${baseUrl}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Login failed");
    }

    const data = await response.json();
    localStorage.setItem("token", data.access_token);

    await checkAuth();
    router.push(takePostLoginPath());
  };

  const completeLogin = async (token: string) => {
    const baseUrl = getBaseHttpUrl();
    const response = await fetch(`${baseUrl}/api/auth/me`, {
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

  const register = async (userData: RegisterData) => {
    const baseUrl = getBaseHttpUrl();
    const response = await fetch(`${baseUrl}/api/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Registration failed");
    }

    await login(userData.username, userData.password);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    router.push("/login");
  };

  const value = {
    user,
    loading,
    login,
    completeLogin,
    register,
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
