"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ClipboardList,
  Clock,
  HeartPulse,
  Loader2,
  Stethoscope,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { healthRecordsApi } from "@/lib/api";
import { ConditionSection } from "@/features/health/ConditionSection";
import { AllergySection } from "@/features/health/AllergySection";
import { SymptomSection } from "@/features/health/SymptomSection";
import { ObservationSection } from "@/features/health/ObservationSection";
import { RevisionHistoryModal } from "@/features/health/RevisionHistoryModal";
import type { HealthObservation, HealthOverview } from "@/types/health";

type TabId = "overview" | "symptoms" | "conditions" | "allergies" | "observations";

export default function MyHealthPage() {
  const router = useRouter();
  const { authenticated, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [historyTarget, setHistoryTarget] = useState<{
    entityType: "condition" | "allergy" | "symptom" | "observation";
    entityId: string;
    title: string;
  } | null>(null);

  useEffect(() => {
    if (!authLoading && !authenticated) {
      router.replace("/login");
    }
  }, [authenticated, authLoading, router]);

  const { data: overview, isLoading: overviewLoading } = useQuery<HealthOverview>({
    queryKey: ["health", "overview"],
    queryFn: healthRecordsApi.getOverview,
    enabled: authenticated,
  });

  const { data: pendingCandidates } = useQuery<HealthObservation[]>({
    queryKey: ["health", "candidates"],
    queryFn: healthRecordsApi.listPendingCandidates,
    enabled: authenticated,
  });

  if (authLoading || !authenticated) {
    return (
      <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-[#2457A6]" />
        </div>
      </div>
    );
  }

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "symptoms", label: "Symptoms", count: overview?.symptoms_count },
    { id: "conditions", label: "Conditions", count: overview?.conditions_count },
    { id: "allergies", label: "Allergies", count: overview?.allergies_count },
    {
      id: "observations",
      label: "Observations",
      count: overview?.observations_count,
    },
  ];

  const openHistory = (
    entityType: "condition" | "allergy" | "symptom" | "observation",
    entityId: string,
    title: string
  ) => {
    setHistoryTarget({ entityType, entityId, title });
  };

  return (
    <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[#172033]">My Health</h1>
            <p className="text-sm text-[#667085] mt-1">
              Patient-controlled longitudinal medical records with preserved provenance and revision history.
            </p>
          </div>
          <Link
            href="/timeline"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white border border-[#E4E7EC] hover:bg-slate-50 text-sm font-medium text-[#2457A6]"
          >
            <Clock className="w-4 h-4" />
            View Chronological Timeline
          </Link>
        </div>

        {/* Pending Extracted Candidates Review Banner (Phase 4) */}
        {pendingCandidates && pendingCandidates.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-2.5 text-sm text-[#946200]">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold">
                  {pendingCandidates.length} extracted observation
                  {pendingCandidates.length === 1 ? "" : "s"} awaiting your
                  confirmation
                </p>
                <p className="text-xs mt-0.5 text-[#946200]/90">
                  Values extracted from uploaded documents remain marked as{" "}
                  <span className="font-mono">candidate</span> until you review
                  and confirm them.
                </p>
              </div>
            </div>
            <Link
              href={
                pendingCandidates[0]?.source_document_id
                  ? `/documents/${pendingCandidates[0].source_document_id}`
                  : "/documents"
              }
              className="inline-flex items-center justify-center px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#946200] hover:bg-amber-800 text-white shrink-0 transition-colors"
            >
              Review Extracted Values
            </Link>
          </div>
        )}

        {/* Subsections Tab Bar */}
        <div
          role="tablist"
          aria-label="My Health sections"
          className="flex flex-wrap gap-2 border-b border-[#E4E7EC] pb-3"
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-[#2457A6] text-white shadow-sm"
                  : "bg-white border border-[#E4E7EC] text-[#667085] hover:text-[#172033] hover:bg-slate-50"
              }`}
            >
              <span>{tab.label}</span>
              {typeof tab.count === "number" && (
                <span
                  className={`text-xs px-1.5 py-0.5 rounded-full ${
                    activeTab === tab.id
                      ? "bg-white/20 text-white"
                      : "bg-slate-100 text-[#667085]"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {overviewLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-[#2457A6]" />
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <button
                    type="button"
                    onClick={() => setActiveTab("conditions")}
                    className="text-left p-5 rounded-xl bg-white border border-[#E4E7EC] shadow-sm hover:border-[#2457A6]/50 transition-colors"
                  >
                    <div className="flex items-center justify-between text-[#2457A6] mb-2">
                      <Stethoscope className="w-5 h-5" />
                      <span className="text-xs font-medium text-[#667085]">
                        {overview?.active_conditions_count ?? 0} active
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-[#172033]">
                      {overview?.conditions_count ?? 0}
                    </div>
                    <div className="text-xs text-[#667085] mt-0.5">
                      Recorded Conditions
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab("allergies")}
                    className="text-left p-5 rounded-xl bg-white border border-[#E4E7EC] shadow-sm hover:border-[#2457A6]/50 transition-colors"
                  >
                    <div className="flex items-center justify-between text-[#B42318] mb-2">
                      <AlertTriangle className="w-5 h-5" />
                      <span className="text-xs font-medium text-[#667085]">
                        Verified
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-[#172033]">
                      {overview?.allergies_count ?? 0}
                    </div>
                    <div className="text-xs text-[#667085] mt-0.5">
                      Known Allergies
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab("symptoms")}
                    className="text-left p-5 rounded-xl bg-white border border-[#E4E7EC] shadow-sm hover:border-[#2457A6]/50 transition-colors"
                  >
                    <div className="flex items-center justify-between text-[#946200] mb-2">
                      <HeartPulse className="w-5 h-5" />
                      <span className="text-xs font-medium text-[#667085]">
                        {overview?.ongoing_symptoms_count ?? 0} ongoing
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-[#172033]">
                      {overview?.symptoms_count ?? 0}
                    </div>
                    <div className="text-xs text-[#667085] mt-0.5">
                      Logged Symptoms
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab("observations")}
                    className="text-left p-5 rounded-xl bg-white border border-[#E4E7EC] shadow-sm hover:border-[#2457A6]/50 transition-colors"
                  >
                    <div className="flex items-center justify-between text-[#157A5B] mb-2">
                      <Activity className="w-5 h-5" />
                      <span className="text-xs font-medium text-[#667085]">
                        Labs & Vitals
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-[#172033]">
                      {overview?.observations_count ?? 0}
                    </div>
                    <div className="text-xs text-[#667085] mt-0.5">
                      Health Observations
                    </div>
                  </button>
                </div>

                {/* Recent Medical Activity */}
                <section className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E4E7EC]">
                    <div className="flex items-center gap-2">
                      <ClipboardList className="w-5 h-5 text-[#2457A6]" />
                      <h2 className="text-base font-semibold text-[#172033]">
                        Recent Health Activity
                      </h2>
                    </div>
                    <Link
                      href="/timeline"
                      className="text-xs font-medium text-[#2457A6] hover:underline"
                    >
                      View all ({overview?.timeline_events_count ?? 0})
                    </Link>
                  </div>

                  {!overview || overview.recent_events.length === 0 ? (
                    <p className="text-sm text-[#667085] py-4">
                      No health events recorded yet. Use the tabs above to add conditions, allergies, symptoms, or observations.
                    </p>
                  ) : (
                    <ul className="divide-y divide-[#E4E7EC]">
                      {overview.recent_events.map((ev) => (
                        <li
                          key={ev.id}
                          className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-blue-50 text-[#2457A6]">
                                {ev.event_category}
                              </span>
                              <span className="text-sm font-medium text-[#172033]">
                                {ev.title}
                              </span>
                            </div>
                            {ev.summary && (
                              <p className="text-xs text-[#667085] mt-1">
                                {ev.summary}
                              </p>
                            )}
                          </div>
                          <span className="text-xs text-[#667085] shrink-0">
                            {new Date(ev.event_occurred_at).toLocaleDateString()}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </>
            )}
          </div>
        )}

        {activeTab === "conditions" && (
          <ConditionSection onOpenHistory={openHistory} />
        )}
        {activeTab === "allergies" && (
          <AllergySection onOpenHistory={openHistory} />
        )}
        {activeTab === "symptoms" && (
          <SymptomSection onOpenHistory={openHistory} />
        )}
        {activeTab === "observations" && (
          <ObservationSection onOpenHistory={openHistory} />
        )}
      </main>

      {historyTarget && (
        <RevisionHistoryModal
          entityType={historyTarget.entityType}
          entityId={historyTarget.entityId}
          title={historyTarget.title}
          onClose={() => setHistoryTarget(null)}
        />
      )}
    </div>
  );
}
