"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, History, Archive, CheckCircle2, Loader2 } from "lucide-react";
import { healthRecordsApi, ApiError } from "@/lib/api";
import type { PatientSymptom } from "@/types/health";

interface SectionProps {
  onOpenHistory: (
    entityType: "condition" | "allergy" | "symptom" | "observation",
    entityId: string,
    title: string
  ) => void;
}

export function SymptomSection({ onOpenHistory }: SectionProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [severity, setSeverity] = useState("moderate");
  const [frequency, setFrequency] = useState("");
  const [bodyLocation, setBodyLocation] = useState("");
  const [startedAt, setStartedAt] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: symptoms = [], isLoading } = useQuery<PatientSymptom[]>({
    queryKey: ["health", "symptoms"],
    queryFn: healthRecordsApi.listSymptoms,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["health"] });
    queryClient.invalidateQueries({ queryKey: ["timeline"] });
  };

  const createMutation = useMutation({
    mutationFn: healthRecordsApi.createSymptom,
    onSuccess: () => {
      setName("");
      setFrequency("");
      setBodyLocation("");
      setStartedAt("");
      setNotes("");
      setError(null);
      invalidateAll();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Could not log symptom."),
  });

  const toggleStatusMutation = useMutation({
    mutationFn: (item: PatientSymptom) =>
      healthRecordsApi.correctSymptom(item.id, {
        status: item.status === "resolved" ? "ongoing" : "resolved",
        correction_reason:
          item.status === "resolved"
            ? "Symptom recurred"
            : "Symptom resolved",
      }),
    onSuccess: invalidateAll,
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) =>
      healthRecordsApi.archiveSymptom(id, "Archived from My Health"),
    onSuccess: invalidateAll,
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createMutation.mutate({
      name: name.trim(),
      severity,
      frequency: frequency.trim() || null,
      body_location: bodyLocation.trim() || null,
      started_at: startedAt ? new Date(startedAt).toISOString() : null,
      notes: notes.trim() || null,
    });
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleCreate}
        className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm space-y-4"
      >
        <h2 className="text-base font-semibold text-[#172033]">
          Log Patient Symptom
        </h2>
        {error && <p className="text-xs text-[#B42318]">{error}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            type="text"
            required
            placeholder="Symptom (e.g., Persistent dry cough)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="sm:col-span-2 px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <select
            aria-label="Symptom severity"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC] bg-white"
          >
            <option value="mild">Mild</option>
            <option value="moderate">Moderate</option>
            <option value="severe">Severe</option>
          </select>
          <input
            type="datetime-local"
            aria-label="Started date and time"
            value={startedAt}
            onChange={(e) => setStartedAt(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            placeholder="Frequency (e.g., Daily evenings)"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            placeholder="Location (optional)"
            value={bodyLocation}
            onChange={(e) => setBodyLocation(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-[#2457A6] hover:bg-[#1D4688] text-white text-sm font-medium disabled:opacity-60"
          >
            {createMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            Log Symptom
          </button>
        </div>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
        </div>
      ) : symptoms.length === 0 ? (
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-8 text-center text-sm text-[#667085]">
          No symptoms logged yet.
        </div>
      ) : (
        <div className="space-y-3">
          {symptoms.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold text-[#172033]">{item.name}</h3>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      item.status === "ongoing"
                        ? "bg-amber-50 text-[#946200] border border-amber-200"
                        : "bg-emerald-50 text-[#157A5B] border border-emerald-200"
                    }`}
                  >
                    {item.status}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-[#667085]">
                    {item.severity}
                  </span>
                </div>
                <p className="text-xs text-[#667085]">
                  Started: {new Date(item.started_at).toLocaleString()}
                  {item.frequency ? ` • ${item.frequency}` : ""}
                  {item.body_location ? ` • ${item.body_location}` : ""}
                </p>
                {item.notes && (
                  <p className="text-sm text-[#172033] pt-1">{item.notes}</p>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => toggleStatusMutation.mutate(item)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#E4E7EC] text-xs font-medium text-[#172033] hover:bg-slate-50"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#157A5B]" />
                  {item.status === "resolved" ? "Reopen" : "Resolve"}
                </button>
                <button
                  type="button"
                  onClick={() => onOpenHistory("symptom", item.id, item.name)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#E4E7EC] text-xs font-medium text-[#2457A6] hover:bg-blue-50"
                >
                  <History className="w-3.5 h-3.5" />
                  History
                </button>
                <button
                  type="button"
                  onClick={() => archiveMutation.mutate(item.id)}
                  aria-label={`Archive ${item.name}`}
                  className="p-1.5 rounded-lg border border-[#E4E7EC] text-[#667085] hover:text-[#B42318] hover:bg-red-50"
                >
                  <Archive className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
