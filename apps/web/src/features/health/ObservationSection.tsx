"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, History, Archive, Pencil, Loader2, X, Check } from "lucide-react";
import { healthRecordsApi, ApiError } from "@/lib/api";
import type { HealthObservation } from "@/types/health";

interface SectionProps {
  onOpenHistory: (
    entityType: "condition" | "allergy" | "symptom" | "observation",
    entityId: string,
    title: string
  ) => void;
}

export function ObservationSection({ onOpenHistory }: SectionProps) {
  const queryClient = useQueryClient();
  const [observationType, setObservationType] = useState("lab_result");
  const [displayName, setDisplayName] = useState("");
  const [valueRaw, setValueRaw] = useState("");
  const [unitRaw, setUnitRaw] = useState("");
  const [referenceRange, setReferenceRange] = useState("");
  const [abnormalityFlag, setAbnormalityFlag] = useState("");
  const [observedAt, setObservedAt] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Inline correction state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editUnit, setEditUnit] = useState("");
  const [editReason, setEditReason] = useState("");

  const { data: observations = [], isLoading } = useQuery<HealthObservation[]>({
    queryKey: ["health", "observations"],
    queryFn: () => healthRecordsApi.listObservations(),
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["health"] });
    queryClient.invalidateQueries({ queryKey: ["timeline"] });
  };

  const createMutation = useMutation({
    mutationFn: healthRecordsApi.createObservation,
    onSuccess: () => {
      setDisplayName("");
      setValueRaw("");
      setUnitRaw("");
      setReferenceRange("");
      setAbnormalityFlag("");
      setObservedAt("");
      setError(null);
      invalidateAll();
    },
    onError: (err) =>
      setError(
        err instanceof ApiError ? err.detail : "Could not record observation."
      ),
  });

  const correctMutation = useMutation({
    mutationFn: ({
      id,
      value_raw,
      unit_raw,
      correction_reason,
    }: {
      id: string;
      value_raw: string;
      unit_raw: string | null;
      correction_reason: string;
    }) =>
      healthRecordsApi.correctObservation(id, {
        value_raw,
        unit_raw,
        correction_reason,
      }),
    onSuccess: () => {
      setEditingId(null);
      invalidateAll();
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) =>
      healthRecordsApi.archiveObservation(id, "Archived from My Health"),
    onSuccess: invalidateAll,
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim() || !valueRaw.trim()) return;
    createMutation.mutate({
      observation_type: observationType,
      display_name: displayName.trim(),
      value_raw: valueRaw.trim(),
      unit_raw: unitRaw.trim() || null,
      reference_range_text: referenceRange.trim() || null,
      abnormality_flag: abnormalityFlag || null,
      observed_at: observedAt ? new Date(observedAt).toISOString() : null,
    });
  };

  const startCorrection = (obs: HealthObservation) => {
    setEditingId(obs.id);
    setEditValue(obs.value_raw);
    setEditUnit(obs.unit_raw || "");
    setEditReason("");
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleCreate}
        className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm space-y-4"
      >
        <h2 className="text-base font-semibold text-[#172033]">
          Record Medical Observation or Lab Result
        </h2>
        {error && <p className="text-xs text-[#B42318]">{error}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <select
            aria-label="Observation type"
            value={observationType}
            onChange={(e) => setObservationType(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC] bg-white"
          >
            <option value="lab_result">Lab Result</option>
            <option value="vital_sign">Vital Sign</option>
            <option value="measurement">Measurement</option>
            <option value="clinical_note">Clinical Note</option>
          </select>
          <input
            type="text"
            required
            placeholder="Test / Metric (e.g., Hemoglobin)"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            required
            placeholder="Value (e.g., 13.5 or 120/80)"
            value={valueRaw}
            onChange={(e) => setValueRaw(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            placeholder="Unit (e.g., g/dL, mmHg)"
            value={unitRaw}
            onChange={(e) => setUnitRaw(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <input
            type="text"
            placeholder="Reference range (e.g., 12.0-16.0 g/dL)"
            value={referenceRange}
            onChange={(e) => setReferenceRange(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <select
            aria-label="Abnormality flag"
            value={abnormalityFlag}
            onChange={(e) => setAbnormalityFlag(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC] bg-white"
          >
            <option value="">Flag (Optional)</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <input
            type="datetime-local"
            aria-label="Observed date and time"
            value={observedAt}
            onChange={(e) => setObservedAt(e.target.value)}
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
            Record Observation
          </button>
        </div>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
        </div>
      ) : observations.length === 0 ? (
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-8 text-center text-sm text-[#667085]">
          No observations recorded yet. Add a lab result or vital sign above.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-[#E4E7EC] shadow-sm overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-[#E4E7EC] bg-[#F7F9FC] text-xs font-semibold text-[#667085]">
                <th className="py-3 px-4">Observation</th>
                <th className="py-3 px-4">Value & Unit</th>
                <th className="py-3 px-4">Reference Range</th>
                <th className="py-3 px-4">Observed Date</th>
                <th className="py-3 px-4">Provenance</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E7EC]">
              {observations.map((obs) => (
                <tr key={obs.id} className="hover:bg-slate-50/70">
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-[#172033]">
                      {obs.display_name}
                    </div>
                    <div className="text-xs text-[#667085]">
                      {obs.observation_type.replace("_", " ")}
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    {editingId === obs.id ? (
                      <div className="flex flex-col gap-1.5">
                        <div className="flex gap-1.5">
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="w-24 px-2 py-1 text-xs rounded border border-[#2457A6]"
                          />
                          <input
                            type="text"
                            placeholder="unit"
                            value={editUnit}
                            onChange={(e) => setEditUnit(e.target.value)}
                            className="w-20 px-2 py-1 text-xs rounded border border-[#E4E7EC]"
                          />
                        </div>
                        <input
                          type="text"
                          placeholder="Correction reason"
                          value={editReason}
                          onChange={(e) => setEditReason(e.target.value)}
                          className="w-48 px-2 py-1 text-xs rounded border border-[#E4E7EC]"
                        />
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-[#172033]">
                          {obs.value_raw}
                          {obs.unit_raw ? ` ${obs.unit_raw}` : ""}
                        </span>
                        {obs.abnormality_flag && (
                          <span
                            className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                              obs.abnormality_flag === "normal"
                                ? "bg-emerald-50 text-[#157A5B]"
                                : obs.abnormality_flag === "critical" ||
                                  obs.abnormality_flag === "high"
                                ? "bg-red-50 text-[#B42318]"
                                : "bg-amber-50 text-[#946200]"
                            }`}
                          >
                            {obs.abnormality_flag}
                          </span>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-xs text-[#667085]">
                    {obs.reference_range_text || "—"}
                  </td>
                  <td className="py-3.5 px-4 text-xs text-[#667085]">
                    {new Date(obs.observed_at).toLocaleDateString()}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-[#667085]">
                      {obs.source_type.replace("_", " ")}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    {editingId === obs.id ? (
                      <div className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() =>
                            correctMutation.mutate({
                              id: obs.id,
                              value_raw: editValue.trim(),
                              unit_raw: editUnit.trim() || null,
                              correction_reason:
                                editReason.trim() || "Patient value correction",
                            })
                          }
                          aria-label="Save correction"
                          className="p-1.5 rounded bg-[#157A5B] text-white"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          aria-label="Cancel correction"
                          className="p-1.5 rounded border border-[#E4E7EC] text-[#667085]"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => startCorrection(obs)}
                          aria-label={`Correct ${obs.display_name}`}
                          className="p-1.5 rounded-lg border border-[#E4E7EC] text-[#667085] hover:text-[#2457A6] hover:bg-blue-50"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            onOpenHistory("observation", obs.id, obs.display_name)
                          }
                          aria-label={`History for ${obs.display_name}`}
                          className="p-1.5 rounded-lg border border-[#E4E7EC] text-[#2457A6] hover:bg-blue-50"
                        >
                          <History className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => archiveMutation.mutate(obs.id)}
                          aria-label={`Archive ${obs.display_name}`}
                          className="p-1.5 rounded-lg border border-[#E4E7EC] text-[#667085] hover:text-[#B42318] hover:bg-red-50"
                        >
                          <Archive className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
