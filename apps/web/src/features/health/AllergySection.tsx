"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, History, Archive, Loader2 } from "lucide-react";
import { healthRecordsApi, ApiError } from "@/lib/api";
import type { PatientAllergy } from "@/types/health";

interface SectionProps {
  onOpenHistory: (
    entityType: "condition" | "allergy" | "symptom" | "observation",
    entityId: string,
    title: string
  ) => void;
}

export function AllergySection({ onOpenHistory }: SectionProps) {
  const queryClient = useQueryClient();
  const [allergen, setAllergen] = useState("");
  const [category, setCategory] = useState("medication");
  const [severity, setSeverity] = useState("moderate");
  const [reaction, setReaction] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: allergies = [], isLoading } = useQuery<PatientAllergy[]>({
    queryKey: ["health", "allergies"],
    queryFn: healthRecordsApi.listAllergies,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["health"] });
    queryClient.invalidateQueries({ queryKey: ["timeline"] });
  };

  const createMutation = useMutation({
    mutationFn: healthRecordsApi.createAllergy,
    onSuccess: () => {
      setAllergen("");
      setReaction("");
      setError(null);
      invalidateAll();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Could not save allergy."),
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) =>
      healthRecordsApi.archiveAllergy(id, "Archived from My Health"),
    onSuccess: invalidateAll,
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!allergen.trim()) return;
    createMutation.mutate({
      allergen: allergen.trim(),
      category,
      severity,
      reaction: reaction.trim() || null,
    });
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleCreate}
        className="bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-sm space-y-4"
      >
        <h2 className="text-base font-semibold text-[#172033]">
          Add Known Allergy
        </h2>
        {error && <p className="text-xs text-[#B42318]">{error}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            type="text"
            required
            placeholder="Allergen (e.g., Penicillin, Peanuts)"
            value={allergen}
            onChange={(e) => setAllergen(e.target.value)}
            className="sm:col-span-2 px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
          />
          <select
            aria-label="Allergy category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC] bg-white"
          >
            <option value="medication">Medication</option>
            <option value="food">Food</option>
            <option value="environmental">Environmental</option>
            <option value="other">Other</option>
          </select>
          <select
            aria-label="Allergy severity"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC] bg-white"
          >
            <option value="mild">Mild</option>
            <option value="moderate">Moderate</option>
            <option value="severe">Severe</option>
            <option value="life_threatening">Life-threatening</option>
          </select>
          <input
            type="text"
            placeholder="Typical reaction (e.g., Rash, swelling)"
            value={reaction}
            onChange={(e) => setReaction(e.target.value)}
            className="sm:col-span-3 px-3.5 py-2 text-sm rounded-lg border border-[#E4E7EC]"
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
            Add Allergy
          </button>
        </div>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
        </div>
      ) : allergies.length === 0 ? (
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-8 text-center text-sm text-[#667085]">
          No allergies recorded yet.
        </div>
      ) : (
        <div className="space-y-3">
          {allergies.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold text-[#172033]">
                    {item.allergen}
                  </h3>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      item.severity === "severe" ||
                      item.severity === "life_threatening"
                        ? "bg-red-50 text-[#B42318] border border-red-200"
                        : "bg-amber-50 text-[#946200] border border-amber-200"
                    }`}
                  >
                    {item.severity.replace("_", " ")}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-[#667085]">
                    {item.category}
                  </span>
                </div>
                {item.reaction && (
                  <p className="text-sm text-[#667085]">
                    Reaction: {item.reaction}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => onOpenHistory("allergy", item.id, item.allergen)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#E4E7EC] text-xs font-medium text-[#2457A6] hover:bg-blue-50"
                >
                  <History className="w-3.5 h-3.5" />
                  History
                </button>
                <button
                  type="button"
                  onClick={() => archiveMutation.mutate(item.id)}
                  aria-label={`Archive ${item.allergen}`}
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
