"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Clock,
  Search,
  Plus,
  ChevronDown,
  ChevronUp,
  Loader2,
  Calendar,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { timelineApi } from "@/lib/api";
import type { TimelineResponse } from "@/types/health";

const CATEGORIES = [
  { id: "", label: "All Events" },
  { id: "observation", label: "Observations" },
  { id: "symptom", label: "Symptoms" },
  { id: "condition", label: "Conditions" },
  { id: "allergy", label: "Allergies" },
  { id: "correction", label: "Corrections" },
  { id: "general", label: "General Updates" },
];

export default function MedicalTimelinePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { authenticated, isLoading: authLoading } = useAuth();

  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Quick patient update form
  const [newTitle, setNewTitle] = useState("");
  const [newSummary, setNewSummary] = useState("");
  const [newDate, setNewDate] = useState("");

  useEffect(() => {
    if (!authLoading && !authenticated) {
      router.replace("/login");
    }
  }, [authenticated, authLoading, router]);

  const { data: timeline, isLoading } = useQuery<TimelineResponse>({
    queryKey: ["timeline", category, search, startDate, endDate],
    queryFn: () =>
      timelineApi.list({
        category: category || undefined,
        q: search.trim() || undefined,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate
          ? new Date(`${endDate}T23:59:59Z`).toISOString()
          : undefined,
        limit: 100,
      }),
    enabled: authenticated,
  });

  const createEventMutation = useMutation({
    mutationFn: timelineApi.createEvent,
    onSuccess: () => {
      setNewTitle("");
      setNewSummary("");
      setNewDate("");
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["health", "overview"] });
    },
  });

  const handleCreateEvent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    createEventMutation.mutate({
      event_category: "general",
      title: newTitle.trim(),
      summary: newSummary.trim() || null,
      event_occurred_at: newDate ? new Date(newDate).toISOString() : null,
    });
  };

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

  return (
    <div className="min-h-screen bg-[#F7F9FC] flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[#172033]">
            Medical Timeline
          </h1>
          <p className="text-sm text-[#667085] mt-1">
            Chronological history of your observations, symptoms, conditions, allergies, and patient-verified corrections.
          </p>
        </div>

        {/* Log General Patient Health Update */}
        <form
          onSubmit={handleCreateEvent}
          className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-sm space-y-3"
        >
          <h2 className="text-sm font-semibold text-[#172033]">
            Add Patient-Reported Health Update
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <input
              type="text"
              required
              placeholder="Event title (e.g., Annual dental checkup)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="sm:col-span-2 px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
            />
            <input
              type="datetime-local"
              aria-label="Event occurrence date"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
              className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
            />
            <input
              type="text"
              placeholder="Summary or notes (optional)"
              value={newSummary}
              onChange={(e) => setNewSummary(e.target.value)}
              className="sm:col-span-2 px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
            />
            <button
              type="submit"
              disabled={createEventMutation.isPending}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white text-sm font-medium disabled:opacity-60"
            >
              {createEventMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
              Add to Timeline
            </button>
          </div>
        </form>

        {/* Filters & Search */}
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-sm space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-[#667085] absolute left-3 top-2.5" />
              <input
                type="search"
                placeholder="Search timeline events..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[#E4E7EC]"
              />
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#667085] shrink-0" />
              <input
                type="date"
                aria-label="Start date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E4E7EC]"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#667085]">to</span>
              <input
                type="date"
                aria-label="End date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[#E4E7EC]"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id || "all"}
                type="button"
                onClick={() => setCategory(cat.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  category === cat.id
                    ? "bg-[#2457A6] text-white"
                    : "bg-[#F7F9FC] text-[#667085] border border-[#E4E7EC] hover:text-[#172033]"
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chronological Event Stream */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-[#2457A6]" />
          </div>
        ) : !timeline || timeline.items.length === 0 ? (
          <div className="bg-white rounded-xl border border-[#E4E7EC] p-10 text-center space-y-2">
            <Clock className="w-8 h-8 text-[#667085] mx-auto" />
            <p className="text-sm font-medium text-[#172033]">
              No timeline events match your current filters
            </p>
            <p className="text-xs text-[#667085]">
              Add medical records in My Health or log an update above to build your timeline.
            </p>
          </div>
        ) : (
          <div className="relative pl-6 border-l-2 border-[#E4E7EC] space-y-4">
            {timeline.items.map((ev) => {
              const isExpanded = expandedId === ev.id;
              return (
                <div
                  key={ev.id}
                  className="relative bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-sm"
                >
                  <span className="w-3 h-3 rounded-full bg-[#2457A6] ring-4 ring-[#F7F9FC] absolute -left-[31px] top-6" />
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-blue-50 text-[#2457A6]">
                          {ev.event_category}
                        </span>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-[#667085]">
                          {ev.source_type.replace("_", " ")}
                        </span>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-50 text-[#157A5B]">
                          {ev.review_status}
                        </span>
                      </div>
                      <h3 className="text-base font-semibold text-[#172033]">
                        {ev.title}
                      </h3>
                      {ev.summary && (
                        <p className="text-sm text-[#667085]">{ev.summary}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div className="text-right">
                        <div className="text-xs font-medium text-[#172033]">
                          {new Date(ev.event_occurred_at).toLocaleDateString()}
                        </div>
                        <div className="text-[11px] text-[#667085]">
                          {new Date(ev.event_occurred_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedId(isExpanded ? null : ev.id)
                        }
                        aria-label="Toggle event details"
                        className="p-1.5 rounded-md border border-[#E4E7EC] text-[#667085] hover:bg-slate-50"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-4 pt-3 border-t border-[#E4E7EC] text-xs text-[#667085] space-y-1.5">
                      <div>
                        <strong>Occurred At:</strong>{" "}
                        {new Date(ev.event_occurred_at).toISOString()}
                      </div>
                      <div>
                        <strong>Recorded At:</strong>{" "}
                        {new Date(ev.created_at).toISOString()}
                      </div>
                      {ev.related_entity_type && (
                        <div>
                          <strong>Linked Record:</strong> {ev.related_entity_type}{" "}
                          <code className="text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">
                            {ev.related_entity_id}
                          </code>
                        </div>
                      )}
                      {ev.metadata_json && (
                        <pre className="mt-2 p-2.5 rounded bg-[#F7F9FC] border border-[#E4E7EC] overflow-x-auto text-[11px] text-[#172033]">
                          {JSON.stringify(ev.metadata_json, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
