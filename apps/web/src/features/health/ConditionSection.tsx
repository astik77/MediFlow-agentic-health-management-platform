"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, History, Archive, CheckCircle2, Loader2 } from "lucide-react";
import { healthRecordsApi, ApiError } from "@/lib/api";
import type { PatientCondition } from "@/types/health";

interface SectionProps {
  onOpenHistory: (
    entityType: "condition" | "allergy" | "symptom" | "observation",
    entityId: string,
    title: string
  ) => void;
}

export function ConditionSection({ onOpenHistory }: SectionProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [status, setStatus] = useState("active");
  const [severity, setSeverity] = useState("");
  const [onsetDate, setOnsetDate] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: conditions = [], isLoading } = useQuery<PatientCondition[]>({
    queryKey: ["health", "conditions"],
    queryFn: healthRecordsApi.listConditions,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["health"] });
    queryClient.invalidateQueries({ queryKey: ["timeline"] });
  };

  const createMutation = useMutation({
    mutationFn: healthRecordsApi.createCondition,
    onSuccess: () => {
      setName("");
      setSeverity("");
      setOnsetDate("");
      setNotes("");
      setError(null);
      invalidateAll();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Could not save condition."),
  });

  const resolveMutation = useMutation({
    mutationFn: (item: PatientCondition) =>
      healthRecordsApi.correctCondition(item.id, {
        status: item.status === "resolved" ? "active" : "resolved",
        correction_reason:
          item.status === "resolved"
            ? "Marked active by patient"
            : "Marked resolved by patient",
      }),
    onSuccess: invalidateAll,
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) =>
      healthRecordsApi.archiveCondition(id, "Archived from My Health"),
    onSuccess: invalidateAll,
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createMutation.mutate({
      name: name.trim(),
      status,
      severity: severity || null,
      onset_date: onsetDate || null,
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
          Add Existing Condition
        </h2>
        {error && <p className="text-xs text-[#B42318]">{error}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            type="text"
            required
            placeholder="Condition name (e.g., Hypertension)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="sm:col-span-2 px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC] focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30"
          />
          <select
            aria-label="Condition status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC] bg-white"
          >
            <option value="active">Active</option>
            <option value="remission">In Remission</option>
            <option value="resolved">Resolved</option>
            <option value="inactive">Inactive</option>
          </select>
          <input
            type="date"
            aria-label="Onset date"
            value={onsetDate}
            onChange={(e) => setOnsetDate(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            placeholder="Severity (optional)"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="sm:col-span-2 lg:col-span-2 px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
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
            Add Condition
          </button>
        </div>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
        </div>
      ) : conditions.length === 0 ? (
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-8 text-center text-sm text-[#667085]">
          No medical conditions recorded yet. Add your first condition above.
        </div>
      ) : (
        <div className="space-y-3">
          {conditions.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold text-[#172033]">{item.name}</h3>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      item.status === "active"
                        ? "bg-amber-50 text-[#946200] border border-amber-200"
                        : "bg-emerald-50 text-[#157A5B] border border-emerald-200"
                    }`}
                  >
                    {item.status}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-[#667085]">
                    {item.source_type.replace("_", " ")}
                  </span>
                </div>
                <p className="text-xs text-[#667085]">
                  {item.onset_date ? `Onset: ${item.onset_date}` : "Onset date not specified"}
                  {item.severity ? ` • Severity: ${item.severity}` : ""}
                </p>
                {item.notes && (
                  <p className="text-sm text-[#172033] pt-1">{item.notes}</p>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => resolveMutation.mutate(item)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#E4E7EC] text-xs font-medium text-[#172033] hover:bg-slate-50"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#157A5B]" />
                  {item.status === "resolved" ? "Reopen" : "Mark Resolved"}
                </button>
                <button
                  type="button"
                  onClick={() => onOpenHistory("condition", item.id, item.name)}
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
