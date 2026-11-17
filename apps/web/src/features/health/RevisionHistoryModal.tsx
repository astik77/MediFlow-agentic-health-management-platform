"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { History, X, Loader2, AlertCircle } from "lucide-react";
import { healthRecordsApi } from "@/lib/api";
import type { RecordRevision } from "@/types/health";

interface RevisionHistoryModalProps {
  entityType: "condition" | "allergy" | "symptom" | "observation";
  entityId: string;
  title: string;
  onClose: () => void;
}

export function RevisionHistoryModal({
  entityType,
  entityId,
  title,
  onClose,
}: RevisionHistoryModalProps) {
  const { data: revisions, isLoading, error } = useQuery<RecordRevision[]>({
    queryKey: ["health", entityType, entityId, "history"],
    queryFn: () => {
      switch (entityType) {
        case "condition":
          return healthRecordsApi.getConditionHistory(entityId);
        case "allergy":
          return healthRecordsApi.getAllergyHistory(entityId);
        case "symptom":
          return healthRecordsApi.getSymptomHistory(entityId);
        case "observation":
          return healthRecordsApi.getObservationHistory(entityId);
      }
    },
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Revision history for ${title}`}
      className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4"
    >
      <div className="bg-white rounded-xl border border-[#E4E7EC] shadow-lg max-w-2xl w-full max-h-[85vh] flex flex-col">
        <div className="px-6 py-4 border-b border-[#E4E7EC] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <History className="w-5 h-5 text-[#2457A6]" />
            <div>
              <h2 className="text-base font-bold text-[#172033]">
                Provenance & Revision History
              </h2>
              <p className="text-xs text-[#667085]">{title}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close revision history"
            className="p-1.5 rounded-md text-[#667085] hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
            </div>
          ) : error ? (
            <div className="p-4 rounded-lg bg-red-50 text-[#B42318] text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Unable to load revision history.
            </div>
          ) : revisions && revisions.length > 0 ? (
            revisions.map((rev) => (
              <div
                key={rev.id}
                className="p-4 rounded-lg border border-[#E4E7EC] bg-[#F7F9FC] space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-100 text-[#2457A6]">
                      Rev #{rev.revision_number}
                    </span>
                    <span className="text-xs font-semibold uppercase tracking-wide text-[#172033]">
                      {rev.action}
                    </span>
                  </div>
                  <span className="text-xs text-[#667085]">
                    {new Date(rev.created_at).toLocaleString()}
                  </span>
                </div>
                {rev.reason && (
                  <p className="text-xs text-[#172033]">
                    <strong>Reason:</strong> {rev.reason}
                  </p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  {rev.previous_data && (
                    <div className="p-2.5 rounded bg-white border border-[#E4E7EC]">
                      <span className="block text-[11px] font-semibold text-[#667085] mb-1">
                        Previous Snapshot
                      </span>
                      <pre className="text-[11px] text-[#667085] overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(rev.previous_data, null, 2)}
                      </pre>
                    </div>
                  )}
                  <div
                    className={`p-2.5 rounded bg-white border border-[#E4E7EC] ${
                      !rev.previous_data ? "sm:col-span-2" : ""
                    }`}
                  >
                    <span className="block text-[11px] font-semibold text-[#157A5B] mb-1">
                      Recorded Snapshot
                    </span>
                    <pre className="text-[11px] text-[#172033] overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(rev.new_data, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-[#667085]">No revisions recorded yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
