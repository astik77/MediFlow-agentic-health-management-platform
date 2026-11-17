"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, Mail, AlertCircle, Loader2, Shield } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { authApi, ApiError } from "@/lib/api";
import { useAuth } from "@/features/auth/AuthContext";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const { refetchAuth } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (values: LoginFormValues) => {
    setServerError(null);
    try {
      await authApi.login(values);
      await refetchAuth();
      const status = await authApi.getMe();
      if (status.authenticated && !status.is_onboarded) {
        router.push("/onboarding");
      } else {
        router.push("/profile");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.detail);
      } else {
        setServerError("Unable to sign in right now. Please try again.");
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md bg-white rounded-xl border border-[#E4E7EC] shadow-sm p-8">
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#2457A6] flex items-center justify-center mb-4">
              <Shield className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-[#172033]">
              Sign in to MEDIFLOW
            </h1>
            <p className="text-sm text-[#667085] mt-1">
              Access your personal longitudinal health records
            </p>
          </div>

          {serverError && (
            <div
              role="alert"
              className="mb-6 p-3.5 rounded-lg bg-red-50 border border-red-200 text-[#B42318] text-sm flex items-start gap-2.5"
            >
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-[#172033] mb-1.5"
              >
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#667085] absolute left-3.5 top-3" />
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="patient@example.com"
                  {...register("email")}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-xs text-[#B42318]">{errors.email.message}</p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-[#172033]"
                >
                  Password
                </label>
                <Link
                  href="/forgot-password"
                  className="text-xs font-medium text-[#2457A6] hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#667085] absolute left-3.5 top-3" />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  {...register("password")}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-[#B42318]">
                  {errors.password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] disabled:opacity-60 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2 shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[#667085]">
            New to MEDIFLOW?{" "}
            <Link
              href="/register"
              className="font-semibold text-[#2457A6] hover:underline"
            >
              Create a patient account
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
