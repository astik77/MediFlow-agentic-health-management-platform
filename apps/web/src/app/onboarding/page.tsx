"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HeartPulse,
  AlertCircle,
  Loader2,
  CheckCircle2,
  ShieldAlert,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { patientApi, ApiError } from "@/lib/api";

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"];

export default function OnboardingPage() {
  const router = useRouter();
  const { authenticated, isLoading, refetchAuth } = useAuth();

  const [dateOfBirth, setDateOfBirth] = useState("");
  const [biologicalSex, setBiologicalSex] = useState("");
  const [bloodGroup, setBloodGroup] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [emergencyName, setEmergencyName] = useState("");
  const [emergencyRelation, setEmergencyRelation] = useState("");
  const [emergencyPhone, setEmergencyPhone] = useState("");
  const [conditionsInput, setConditionsInput] = useState("");
  const [allergiesInput, setAllergiesInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && !authenticated) {
      router.replace("/login");
    }
  }, [authenticated, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const parseCommaList = (val: string) =>
        val
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);

      const emergencyContact =
        emergencyName.trim() && emergencyRelation.trim() && emergencyPhone.trim()
          ? {
              name: emergencyName.trim(),
              relationship: emergencyRelation.trim(),
              phone_number: emergencyPhone.trim(),
            }
          : null;

      await patientApi.completeOnboarding({
        date_of_birth: dateOfBirth || null,
        biological_sex: biologicalSex || null,
        blood_group: bloodGroup || null,
        height_cm: heightCm ? parseFloat(heightCm) : null,
        weight_kg: weightKg ? parseFloat(weightKg) : null,
        emergency_contact: emergencyContact,
        existing_conditions: parseCommaList(conditionsInput),
        known_allergies: parseCommaList(allergiesInput),
      });

      await refetchAuth();
      router.push("/profile");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Failed to save onboarding baseline. Please check your entries."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading || !authenticated) {
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
      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-10">
        <div className="bg-white rounded-xl border border-[#E4E7EC] shadow-sm p-8">
          <div className="flex items-start gap-4 mb-8 pb-6 border-b border-[#E4E7EC]">
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-[#2457A6] flex items-center justify-center shrink-0">
              <HeartPulse className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#172033]">
                Complete Your Health Baseline
              </h1>
              <p className="text-sm text-[#667085] mt-1">
                All fields are optional and remain under your control. You can update or correct them anytime from your profile.
              </p>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-6 p-3.5 rounded-lg bg-red-50 border border-red-200 text-[#B42318] text-sm flex items-start gap-2.5"
            >
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Demographics & Vitals */}
            <section>
              <h2 className="text-base font-semibold text-[#172033] mb-4">
                Personal & Physical Baseline
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="dob"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Date of Birth
                  </label>
                  <input
                    id="dob"
                    type="date"
                    value={dateOfBirth}
                    onChange={(e) => setDateOfBirth(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>

                <div>
                  <label
                    htmlFor="sex"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Sex (Optional)
                  </label>
                  <select
                    id="sex"
                    value={biologicalSex}
                    onChange={(e) => setBiologicalSex(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] bg-white focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  >
                    <option value="">Prefer not to specify</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="blood-group"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Blood Group
                  </label>
                  <select
                    id="blood-group"
                    value={bloodGroup}
                    onChange={(e) => setBloodGroup(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] bg-white focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  >
                    <option value="">Select blood group</option>
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
                      htmlFor="height"
                      className="block text-sm font-medium text-[#172033] mb-1.5"
                    >
                      Height (cm)
                    </label>
                    <input
                      id="height"
                      type="number"
                      step="0.1"
                      min="30"
                      max="300"
                      placeholder="170"
                      value={heightCm}
                      onChange={(e) => setHeightCm(e.target.value)}
                      className="w-full px-3 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="weight"
                      className="block text-sm font-medium text-[#172033] mb-1.5"
                    >
                      Weight (kg)
                    </label>
                    <input
                      id="weight"
                      type="number"
                      step="0.1"
                      min="1"
                      max="500"
                      placeholder="68"
                      value={weightKg}
                      onChange={(e) => setWeightKg(e.target.value)}
                      className="w-full px-3 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                    />
                  </div>
                </div>
              </div>
            </section>

            {/* Medical Background */}
            <section className="pt-6 border-t border-[#E4E7EC]">
              <h2 className="text-base font-semibold text-[#172033] mb-4">
                Known Conditions & Allergies
              </h2>
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="conditions"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Existing Conditions (comma-separated)
                  </label>
                  <input
                    id="conditions"
                    type="text"
                    placeholder="e.g., Hypertension, Type 2 Diabetes, Asthma"
                    value={conditionsInput}
                    onChange={(e) => setConditionsInput(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
                <div>
                  <label
                    htmlFor="allergies"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Known Allergies (comma-separated)
                  </label>
                  <input
                    id="allergies"
                    type="text"
                    placeholder="e.g., Penicillin, Sulfa drugs, Peanuts"
                    value={allergiesInput}
                    onChange={(e) => setAllergiesInput(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
              </div>
            </section>

            {/* Emergency Contact */}
            <section className="pt-6 border-t border-[#E4E7EC]">
              <h2 className="text-base font-semibold text-[#172033] mb-4">
                Emergency Contact
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label
                    htmlFor="ec-name"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Contact Name
                  </label>
                  <input
                    id="ec-name"
                    type="text"
                    placeholder="Priya Sharma"
                    value={emergencyName}
                    onChange={(e) => setEmergencyName(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
                <div>
                  <label
                    htmlFor="ec-relation"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Relationship
                  </label>
                  <input
                    id="ec-relation"
                    type="text"
                    placeholder="Spouse / Parent"
                    value={emergencyRelation}
                    onChange={(e) => setEmergencyRelation(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
                <div>
                  <label
                    htmlFor="ec-phone"
                    className="block text-sm font-medium text-[#172033] mb-1.5"
                  >
                    Phone Number
                  </label>
                  <input
                    id="ec-phone"
                    type="tel"
                    placeholder="+91-9876543210"
                    value={emergencyPhone}
                    onChange={(e) => setEmergencyPhone(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                  />
                </div>
              </div>
            </section>

            {/* Privacy Notice */}
            <div className="p-4 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] flex items-start gap-3 text-xs text-[#667085]">
              <ShieldAlert className="w-4 h-4 text-[#2457A6] shrink-0 mt-0.5" />
              <p>
                <strong>Privacy-First Storage:</strong> Your baseline information is stored strictly under your private patient profile. External AI APIs are disabled by default for real patient records.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => router.push("/profile")}
                className="px-4 py-2.5 rounded-lg border border-[#E4E7EC] text-sm font-medium text-[#667085] hover:bg-slate-50"
              >
                Skip for now
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] disabled:opacity-60 text-white text-sm font-medium shadow-sm"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving Baseline...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Save & Continue to Profile
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
