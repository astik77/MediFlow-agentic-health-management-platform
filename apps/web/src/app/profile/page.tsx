"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  User as UserIcon,
  Shield,
  KeyRound,
  LogOut,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Fingerprint,
  Save,
  Cpu,
  Lock,
  Download,
  Trash2,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { aiApi, authApi, patientApi, ApiError } from "@/lib/api";
import type { AIStatusResponse } from "@/types/ai";
import type { PatientProfile, ProfileUpdatePayload } from "@/types/auth";

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"];

export default function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { authenticated, user, isLoading: authLoading, logout } = useAuth();

  const [fullName, setFullName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [biologicalSex, setBiologicalSex] = useState("");
  const [bloodGroup, setBloodGroup] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [conditionsInput, setConditionsInput] = useState("");
  const [allergiesInput, setAllergiesInput] = useState("");
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [revoking, setRevoking] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showDeleteForm, setShowDeleteForm] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!authLoading && !authenticated) {
      router.replace("/login");
    }
  }, [authenticated, authLoading, router]);

  const {
    data: profile,
    isLoading: profileLoading,
    error: profileError,
  } = useQuery<PatientProfile>({
    queryKey: ["patient", "profile"],
    queryFn: patientApi.getProfile,
    enabled: authenticated,
  });

  const { data: aiStatus } = useQuery<AIStatusResponse>({
    queryKey: ["ai", "status"],
    queryFn: aiApi.getStatus,
    enabled: authenticated,
  });

  useEffect(() => {
    if (profile) {
      setFullName(profile.full_name || "");
      setDateOfBirth(profile.date_of_birth || "");
      setBiologicalSex(profile.biological_sex || "");
      setBloodGroup(profile.blood_group || "");
      setHeightCm(profile.height_cm !== null ? String(profile.height_cm) : "");
      setWeightKg(profile.weight_kg !== null ? String(profile.weight_kg) : "");
      setConditionsInput(
        (profile.medical_baseline?.existing_conditions || []).join(", ")
      );
      setAllergiesInput(
        (profile.medical_baseline?.known_allergies || []).join(", ")
      );
    }
  }, [profile]);

  const updateMutation = useMutation({
    mutationFn: (payload: ProfileUpdatePayload) =>
      patientApi.updateProfile(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["patient", "profile"], updated);
      setFeedback({
        type: "success",
        message: "Patient profile updated successfully.",
      });
    },
    onError: (err) => {
      setFeedback({
        type: "error",
        message:
          err instanceof ApiError
            ? err.detail
            : "Failed to save profile changes.",
      });
    },
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);

    const parseCommaList = (val: string) =>
      val
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

    updateMutation.mutate({
      full_name: fullName.trim() || undefined,
      date_of_birth: dateOfBirth || null,
      biological_sex: biologicalSex || null,
      blood_group: bloodGroup || null,
      height_cm: heightCm ? parseFloat(heightCm) : null,
      weight_kg: weightKg ? parseFloat(weightKg) : null,
      medical_baseline: {
        ...(profile?.medical_baseline || {}),
        existing_conditions: parseCommaList(conditionsInput),
        known_allergies: parseCommaList(allergiesInput),
      },
    });
  };

  const handleRevokeAllSessions = async () => {
    setRevoking(true);
    setFeedback(null);
    try {
      await authApi.revokeAllSessions();
      await logout();
      router.push("/login");
    } catch (err) {
      setFeedback({
        type: "error",
        message:
          err instanceof ApiError ? err.detail : "Failed to revoke sessions.",
      });
      setRevoking(false);
    }
  };

  const handleExportVault = async () => {
    setExporting(true);
    setFeedback(null);
    try {
      const bundle = await patientApi.exportData();
      const blob = new Blob([JSON.stringify(bundle, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      const today = new Date().toISOString().slice(0, 10);
      anchor.href = url;
      anchor.download = `mediflow-health-export-${today}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setFeedback({
        type: "success",
        message: "Health vault exported successfully as JSON.",
      });
    } catch (err) {
      setFeedback({
        type: "error",
        message:
          err instanceof ApiError
            ? err.detail
            : "Failed to export health vault.",
      });
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setDeleting(true);
    setFeedback(null);
    try {
      await patientApi.deleteAccount({
        password: deletePassword,
        confirm_text: deleteConfirmText,
      });
      await logout();
      router.replace("/register");
    } catch (err) {
      setFeedback({
        type: "error",
        message:
          err instanceof ApiError
            ? err.detail
            : "Failed to delete account. Check your password and confirmation phrase.",
      });
      setDeleting(false);
    }
  };

  if (authLoading || !authenticated || profileLoading) {
    return (
      <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-[#2457A6]" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-10 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[#172033]">
              My Profile & Account Security
            </h1>
            <p className="text-sm text-[#667085] mt-1">
              Manage your personal health baseline, unique patient identifier, and session controls.
            </p>
          </div>
          {profile && !profile.is_onboarded && (
            <Link
              href="/onboarding"
              className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-amber-50 text-[#946200] border border-amber-200 text-sm font-medium hover:bg-amber-100"
            >
              Finish Onboarding Wizard
            </Link>
          )}
        </div>

        {profileError && (
          <div
            role="alert"
            className="p-4 rounded-lg bg-red-50 border border-red-200 text-[#B42318] text-sm flex items-center gap-2.5"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Unable to load patient profile.</span>
          </div>
        )}

        {feedback && (
          <div
            role="status"
            className={`p-4 rounded-lg border text-sm flex items-center gap-2.5 ${
              feedback.type === "success"
                ? "bg-emerald-50 border-emerald-200 text-[#157A5B]"
                : "bg-red-50 border-red-200 text-[#B42318]"
            }`}
          >
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
        )}

        {/* Unique Patient Identifier Card */}
        {profile && (
          <section className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-[#2457A6] flex items-center justify-center shrink-0">
                <Fingerprint className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-sm font-semibold text-[#172033]">
                  Immutable Patient Identifier
                </h2>
                <p className="text-xs text-[#667085] mt-0.5">
                  Account Email: <span className="font-medium text-[#172033]">{user?.email}</span>
                </p>
                <div className="mt-2.5 px-3 py-2 rounded-md bg-[#F7F9FC] border border-[#E4E7EC] font-mono text-xs text-[#172033] break-all">
                  {profile.id}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Editable Demographics Form */}
        <section className="bg-white rounded-xl border border-[#E4E7EC] p-6 sm:p-8 shadow-sm">
          <div className="flex items-center gap-2.5 mb-6 pb-4 border-b border-[#E4E7EC]">
            <UserIcon className="w-5 h-5 text-[#2457A6]" />
            <h2 className="text-lg font-semibold text-[#172033]">
              Personal & Medical Baseline
            </h2>
          </div>

          <form onSubmit={handleSave} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label
                  htmlFor="profile-fullname"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Full Name
                </label>
                <input
                  id="profile-fullname"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>

              <div>
                <label
                  htmlFor="profile-dob"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Date of Birth
                </label>
                <input
                  id="profile-dob"
                  type="date"
                  value={dateOfBirth}
                  onChange={(e) => setDateOfBirth(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>

              <div>
                <label
                  htmlFor="profile-sex"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Sex
                </label>
                <select
                  id="profile-sex"
                  value={biologicalSex}
                  onChange={(e) => setBiologicalSex(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] bg-white focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                >
                  <option value="">Not specified</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="profile-blood"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Blood Group
                </label>
                <select
                  id="profile-blood"
                  value={bloodGroup}
                  onChange={(e) => setBloodGroup(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] bg-white focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                >
                  <option value="">Not specified</option>
                  {BLOOD_GROUPS.map((bg) => (
                    <option key={bg} value={bg}>
                      {bg}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="profile-height"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Height (cm)
                  </label>
                  <input
                    id="profile-height"
                    type="number"
                    step="0.1"
                    min="30"
                    max="300"
                    value={heightCm}
                    onChange={(e) => setHeightCm(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
                <div>
                  <label
                    htmlFor="profile-weight"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Weight (kg)
                  </label>
                  <input
                    id="profile-weight"
                    type="number"
                    step="0.1"
                    min="1"
                    max="500"
                    value={weightKg}
                    onChange={(e) => setWeightKg(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
              </div>

              <div className="sm:col-span-2">
                <label
                  htmlFor="profile-conditions"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Existing Conditions (Patient-Provided, comma-separated)
                </label>
                <input
                  id="profile-conditions"
                  type="text"
                  placeholder="e.g., Hypertension, Asthma"
                  value={conditionsInput}
                  onChange={(e) => setConditionsInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>

              <div className="sm:col-span-2">
                <label
                  htmlFor="profile-allergies"
                  className="block text-sm font-medium text-[#172033] mb-1.5"
                >
                  Known Allergies (Patient-Provided, comma-separated)
                </label>
                <input
                  id="profile-allergies"
                  type="text"
                  placeholder="e.g., Penicillin, Peanuts"
                  value={allergiesInput}
                  onChange={(e) => setAllergiesInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={updateMutation.isPending}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] disabled:opacity-60 text-white text-sm font-medium shadow-sm"
              >
                {updateMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Profile Changes
                  </>
                )}
              </button>
            </div>
          </form>
        </section>

        {/* Account Security & Sessions Card */}
        <section className="bg-white rounded-xl border border-[#E4E7EC] p-6 sm:p-8 shadow-sm">
          <div className="flex items-center gap-2.5 mb-6 pb-4 border-b border-[#E4E7EC]">
            <Shield className="w-5 h-5 text-[#157A5B]" />
            <h2 className="text-lg font-semibold text-[#172033]">
              Account Security & Session Management
            </h2>
          </div>

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC]">
              <div>
                <h3 className="text-sm font-semibold text-[#172033]">
                  Password Recovery & Rotation
                </h3>
                <p className="text-xs text-[#667085] mt-0.5">
                  Protected with Argon2id hashing. Updating your password automatically invalidates all active sessions.
                </p>
              </div>
              <Link
                href="/forgot-password"
                className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg border border-[#E4E7EC] bg-white hover:bg-slate-50 text-xs font-medium text-[#172033] shrink-0"
              >
                <KeyRound className="w-3.5 h-3.5" />
                Reset Password
              </Link>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg bg-red-50/40 border border-red-200/70">
              <div>
                <h3 className="text-sm font-semibold text-[#B42318]">
                  Revoke All Active Sessions
                </h3>
                <p className="text-xs text-[#667085] mt-0.5">
                  Immediately sign out from every browser and device currently logged into your account.
                </p>
              </div>
              <button
                type="button"
                onClick={handleRevokeAllSessions}
                disabled={revoking}
                className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#B42318] hover:bg-red-800 disabled:opacity-60 text-white text-xs font-medium shrink-0"
              >
                {revoking ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <LogOut className="w-3.5 h-3.5" />
                )}
                Revoke All Sessions
              </button>
            </div>
          </div>
        </section>

        {/* Local AI Runtime & Privacy Status (Phase 5) */}
        {aiStatus && (
          <section className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-[#2457A6]" />
                <h2 className="text-base font-bold text-[#172033]">
                  Local AI Runtime &amp; Privacy Controls
                </h2>
              </div>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-[#157A5B] border border-emerald-200">
                <Lock className="w-3.5 h-3.5" />
                {aiStatus.privacy_policy.allow_external_ai_for_real_data
                  ? "External AI Permitted"
                  : "Local-First · External AI Blocked on Real Data"}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC]">
                <p className="text-[#667085]">Default Generation Model</p>
                <p className="font-mono font-semibold text-[#172033] mt-1">
                  {aiStatus.default_model}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC]">
                <p className="text-[#667085]">Embedding Model</p>
                <p className="font-mono font-semibold text-[#172033] mt-1">
                  {aiStatus.embedding_model}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC]">
                <p className="text-[#667085]">Versioned Prompts</p>
                <p className="font-semibold text-[#172033] mt-1">
                  {aiStatus.prompt_registry.length} registered templates
                </p>
              </div>
            </div>

            <div className="space-y-2">
              {aiStatus.providers.map((p) => (
                <div
                  key={p.provider}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3.5 py-2.5 rounded-lg border border-[#E4E7EC] text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-semibold uppercase text-[#172033]">
                      {p.provider}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-[#475467]">
                      {p.is_local ? "Local" : "External (Synthetic Only)"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[#667085]">{p.detail}</span>
                    <span
                      className={`font-semibold px-2 py-0.5 rounded-full ${
                        p.available
                          ? "bg-emerald-50 text-[#157A5B]"
                          : "bg-slate-100 text-[#667085]"
                      }`}
                    >
                      {p.available ? "Online" : "Offline"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Data Portability & Right to Erasure (Phase 9) */}
        <section className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-[#2457A6]" />
            <h2 className="text-base font-bold text-[#172033]">
              Data Portability &amp; Account Erasure
            </h2>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC]">
            <div>
              <h3 className="text-sm font-semibold text-[#172033]">
                Export My Health Vault (JSON)
              </h3>
              <p className="text-xs text-[#667085] mt-0.5">
                Download a complete, portable JSON copy of your profile,
                conditions, allergies, symptoms, observations, timeline,
                documents metadata, conversations, and 7-day summaries.
              </p>
            </div>
            <button
              type="button"
              onClick={handleExportVault}
              disabled={exporting}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] disabled:opacity-60 text-white text-xs font-medium shrink-0"
            >
              {exporting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Download className="w-3.5 h-3.5" />
              )}
              Export JSON
            </button>
          </div>

          <div className="p-4 rounded-lg bg-red-50/50 border border-red-200 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-[#B42318]">
                  Permanently Delete Account
                </h3>
                <p className="text-xs text-[#667085] mt-0.5">
                  Permanently removes your account, all medical records,
                  uploaded document files on disk, vector embeddings, and
                  conversations. This action cannot be undone.
                </p>
              </div>
              {!showDeleteForm && (
                <button
                  type="button"
                  onClick={() => setShowDeleteForm(true)}
                  className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg border border-red-300 bg-white hover:bg-red-50 text-[#B42318] text-xs font-medium shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete Account
                </button>
              )}
            </div>

            {showDeleteForm && (
              <form
                onSubmit={handleDeleteAccount}
                className="pt-3 border-t border-red-200/80 space-y-3"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="delete-password"
                      className="block text-xs font-medium text-[#172033] mb-1"
                    >
                      Current Password
                    </label>
                    <input
                      id="delete-password"
                      type="password"
                      required
                      value={deletePassword}
                      onChange={(e) => setDeletePassword(e.target.value)}
                      placeholder="Enter your password"
                      className="w-full rounded-lg border border-[#D0D5DD] bg-white px-3 py-2 text-xs text-[#172033]"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="delete-confirm"
                      className="block text-xs font-medium text-[#172033] mb-1"
                    >
                      Type <code className="font-mono">DELETE MY ACCOUNT</code>
                    </label>
                    <input
                      id="delete-confirm"
                      type="text"
                      required
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      placeholder="DELETE MY ACCOUNT"
                      className="w-full rounded-lg border border-[#D0D5DD] bg-white px-3 py-2 text-xs text-[#172033]"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="submit"
                    disabled={
                      deleting || deleteConfirmText.trim() !== "DELETE MY ACCOUNT"
                    }
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#B42318] hover:bg-red-800 disabled:opacity-50 text-white text-xs font-medium"
                  >
                    {deleting ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="w-3.5 h-3.5" />
                    )}
                    Confirm Permanent Deletion
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowDeleteForm(false);
                      setDeletePassword("");
                      setDeleteConfirmText("");
                    }}
                    className="px-3 py-2 rounded-lg border border-[#E4E7EC] bg-white text-xs font-medium text-[#667085] hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
