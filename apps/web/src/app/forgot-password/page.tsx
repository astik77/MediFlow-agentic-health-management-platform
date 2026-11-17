"use client";

import React, { useState } from "react";
import Link from "next/link";
import { KeyRound, Mail, Lock, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { authApi, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<"request" | "confirm" | "done">("request");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [devTokenNotice, setDevTokenNotice] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.requestPasswordReset(email);
      if (res.dev_reset_token) {
        setToken(res.dev_reset_token);
        setDevTokenNotice(res.dev_reset_token);
      }
      setStep("confirm");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not process request."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await authApi.confirmPasswordReset(token, newPassword);
      setStep("done");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Invalid or expired recovery token."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md bg-white rounded-xl border border-[#E4E7EC] shadow-sm p-8">
          <div className="flex flex-col items-center text-center mb-6">
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#2457A6] flex items-center justify-center mb-4">
              <KeyRound className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold text-[#172033]">
              Password Recovery
            </h1>
            <p className="text-sm text-[#667085] mt-1">
              {step === "request" &&
                "Enter your email to generate a one-time recovery token."}
              {step === "confirm" &&
                "Enter your recovery token and choose a new password."}
              {step === "done" && "Your password has been securely updated."}
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-5 p-3.5 rounded-lg bg-red-50 border border-red-200 text-[#B42318] text-sm flex items-start gap-2.5"
            >
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {step === "request" && (
            <form onSubmit={handleRequest} className="space-y-4">
              <div>
                <label
                  htmlFor="reset-email"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[#667085] absolute left-3.5 top-3" />
                  <input
                    id="reset-email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="patient@example.com"
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] disabled:opacity-60 text-white font-medium text-sm flex items-center justify-center gap-2"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Request Recovery Token
              </button>
            </form>
          )}

          {step === "confirm" && (
            <form onSubmit={handleConfirm} className="space-y-4">
              {devTokenNotice && (
                <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-xs text-[#2457A6] break-all">
                  <strong>Dev Mode Recovery Token:</strong> {devTokenNotice}
                </div>
              )}
              <div>
                <label
                  htmlFor="reset-token"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Recovery Token
                </label>
                <input
                  id="reset-token"
                  type="text"
                  required
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Paste your one-time recovery token"
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>
              <div>
                <label
                  htmlFor="new-password"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  New Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#667085] absolute left-3.5 top-3" />
                  <input
                    id="new-password"
                    type="password"
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] disabled:opacity-60 text-white font-medium text-sm flex items-center justify-center gap-2"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Update Password
              </button>
            </form>
          )}

          {step === "done" && (
            <div className="text-center space-y-4">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-50 text-[#157A5B]">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <p className="text-sm text-[#667085]">
                All previous sessions have been revoked for your security.
              </p>
              <Link
                href="/login"
                className="inline-block w-full py-2.5 px-4 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white font-medium text-sm"
              >
                Return to Sign In
              </Link>
            </div>
          )}

          {step !== "done" && (
            <p className="mt-6 text-center text-sm text-[#667085]">
              Remembered your password?{" "}
              <Link
                href="/login"
                className="font-semibold text-[#2457A6] hover:underline"
              >
                Sign in
              </Link>
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
