"use client";

import React, { createContext, useContext } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api";
import type { AuthStatus, User } from "@/types/auth";

interface AuthContextValue {
  authenticated: boolean;
  user: User | null;
  patientId: string | null;
  isOnboarded: boolean;
  isLoading: boolean;
  refetchAuth: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery<AuthStatus>({
    queryKey: ["auth", "me"],
    queryFn: authApi.getMe,
    retry: false,
    staleTime: 60 * 1000,
  });

  const refetchAuth = async () => {
    await refetch();
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      queryClient.setQueryData<AuthStatus>(["auth", "me"], {
        authenticated: false,
        user: null,
        patient_id: null,
        is_onboarded: false,
      });
      queryClient.removeQueries({ queryKey: ["patient"] });
    }
  };

  const value: AuthContextValue = {
    authenticated: data?.authenticated ?? false,
    user: data?.user ?? null,
    patientId: data?.patient_id ?? null,
    isOnboarded: data?.is_onboarded ?? false,
    isLoading,
    refetchAuth,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
