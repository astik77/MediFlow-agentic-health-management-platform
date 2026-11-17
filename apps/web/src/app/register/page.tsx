"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  User as UserIcon,
  Mail,
  Lock,
  AlertCircle,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { authApi, ApiError } from "@/lib/api";
import { useAuth } from "@/features/auth/AuthContext";

const registerSchema = z
  .object({
    full_name: z
      .string()
      .min(2, "Full name must be at least 2 characters.")
      .max(255),
    email: z.string().email("Please enter a valid email address."),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters.")
      .max(128),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { refetchAuth } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError(null);
    try {
      await authApi.register({
        full_name: values.full_name,
        email: values.email,
        password: values.password,
      });
      // Automatically sign in the newly created patient and send to onboarding
      await authApi.login({
        email: values.email,
        password: values.password,
      });
      await refetchAuth();
      router.push("/onboarding");
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.detail);
      } else {
        setServerError("Registration failed. Please try again.");
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md bg-white rounded-xl border border-[#E4E7EC] shadow-sm p-8">
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-[#157A5B] flex items-center justify-center mb-4">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-[#172033]">
              Create your MEDIFLOW account
            </h1>
            <p className="text-sm text-[#667085] mt-1">
              Patient-controlled, privacy-first health management
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

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <label
                htmlFor="full_name"
                className="block text-sm font-medium text-[#172033] mb-1.5"
              >
                Full Name
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-[#667085] absolute left-3.5 top-3" />
                <input
                  id="full_name"
                  type="text"
                  autoComplete="name"
                  placeholder="Aarav Sharma"
                  {...register("full_name")}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>
              {errors.full_name && (
                <p className="mt-1 text-xs text-[#B42318]">
                  {errors.full_name.message}
                </p>
              )}
            </div>

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
              <label
                htmlFor="password"
                className="block text-sm font-medium text-[#172033] mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#667085] absolute left-3.5 top-3" />
                <input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Minimum 8 characters"
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

            <div>
              <label
                htmlFor="confirm_password"
                className="block text-sm font-medium text-[#172033] mb-1.5"
              >
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#667085] absolute left-3.5 top-3" />
                <input
                  id="confirm_password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Re-enter your password"
                  {...register("confirm_password")}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>
              {errors.confirm_password && (
                <p className="mt-1 text-xs text-[#B42318]">
                  {errors.confirm_password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] disabled:opacity-60 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2 shadow-sm mt-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                "Create Patient Account"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[#667085]">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-semibold text-[#2457A6] hover:underline"
            >
              Sign in
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
