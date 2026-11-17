"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Pencil,
  Sparkles,
  Download,
  FileText,
  ShieldAlert,
  Loader2,
  RefreshCw,
  AlertCircle,
  Check,
  X,
  Bot,
  BookOpen,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { aiApi, ApiError, documentsApi } from "@/lib/api";
import type { DocumentSummaryApiResponse } from "@/types/ai";
import type { DocumentExtractionResponse } from "@/types/documents";
import type { HealthObservation } from "@/types/health";

function abnormalityBadge(flag: string | null): string {
  switch (flag) {
    case "critical":
    case "high":
      return "bg-red-50 text-[#B42318] border-red-200";
    case "low":
      return "bg-amber-50 text-[#946200] border-amber-200";
    case "normal":
      return "bg-emerald-50 text-[#157A5B] border-emerald-200";
    default:
      return "bg-slate-100 text-[#475467] border-slate-200";
  }
}

export default function DocumentExtractionPage() {
  const params = useParams<{ id: string }>();
  const documentId = params?.id || "";
  const router = useRouter();
  const queryClient = useQueryClient();
  const { authenticated, isLoading: authLoading } = useAuth();

  const [selectedPageIdx, setSelectedPageIdx] = useState<number>(0);
  const [statusMsg, setStatusMsg] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // Inline edit state for edit_confirm
  const [editingObsId, setEditingObsId] = useState<string | null>(null);
  const [editName, setEditName] = useState<string>("");
  const [editValue, setEditValue] = useState<string>("");
  const [editUnit, setEditUnit] = useState<string>("");
  const [editRange, setEditRange] = useState<string>("");
  const [editReason, setEditReason] = useState<string>("");
  const [aiSummary, setAiSummary] = useState<DocumentSummaryApiResponse | null>(
    null
  );
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !authenticated) {
      router.replace("/login");
    }
  }, [authenticated, authLoading, router]);

  const {
    data: extraction,
    isLoading,
    error,
  } = useQuery<DocumentExtractionResponse>({
    queryKey: ["document-extraction", documentId],
    queryFn: () => documentsApi.getExtraction(documentId),
    enabled: authenticated && Boolean(documentId),
  });

  const processMutation = useMutation({
    mutationFn: (force: boolean) => documentsApi.process(documentId, force),
    onSuccess: (job) => {
      const extracted = Number(job.metrics_json?.candidates_extracted ?? 0);
      setStatusMsg({
        type: "success",
        text: `Analysis complete (${job.metrics_json?.pages_processed ?? 0} page(s) processed, ${extracted} candidate observation(s) extracted).`,
      });
      setSelectedPageIdx(0);
      queryClient.invalidateQueries({
        queryKey: ["document-extraction", documentId],
      });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["health", "candidates"] });
    },
    onError: (err: unknown) => {
      setStatusMsg({
        type: "error",
        text:
          err instanceof ApiError
            ? err.detail
            : "Document processing failed. Please retry.",
      });
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({
      obsId,
      action,
      overrides,
    }: {
      obsId: string;
      action: "confirm" | "edit_confirm" | "reject";
      overrides?: {
        display_name?: string;
        value_raw?: string;
        unit_raw?: string | null;
        reference_range_text?: string | null;
        reason?: string | null;
      };
    }) =>
      documentsApi.reviewCandidate(documentId, obsId, {
        action,
        ...overrides,
      }),
    onSuccess: (updated) => {
      setEditingObsId(null);
      setStatusMsg({
        type: "success",
        text:
          updated.review_status === "confirmed"
            ? `"${updated.display_name}" confirmed and added to your medical history.`
            : `"${updated.display_name}" rejected and archived.`,
      });
      queryClient.invalidateQueries({
        queryKey: ["document-extraction", documentId],
      });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["health"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
    onError: (err: unknown) => {
      setStatusMsg({
        type: "error",
        text:
          err instanceof ApiError
            ? err.detail
            : "Could not apply review decision.",
      });
    },
  });

  const summarizeMutation = useMutation({
    mutationFn: () => aiApi.summarizeDocument(documentId),
    onSuccess: (res) => {
      setAiSummary(res);
      setAiError(null);
    },
    onError: (err: unknown) => {
      setAiError(
        err instanceof ApiError
          ? err.detail
          : "Unable to generate AI summary. Verify local Ollama is running."
      );
    },
  });

  const startEditing = (obs: HealthObservation) => {
    setEditingObsId(obs.id);
    setEditName(obs.display_name);
    setEditValue(obs.value_raw);
    setEditUnit(obs.unit_raw || "");
    setEditRange(obs.reference_range_text || "");
    setEditReason("");
  };

  if (authLoading || !authenticated || isLoading) {
    return (
      <div className="min-h-screen bg-[#F7F9FC]">
        <Navbar />
        <div className="flex items-center justify-center py-24 text-[#667085] gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
          Loading document intelligence workspace...
        </div>
      </div>
    );
  }

  if (error || !extraction) {
    return (
      <div className="min-h-screen bg-[#F7F9FC]">
        <Navbar />
        <main className="max-w-4xl mx-auto px-6 py-12 space-y-4">
          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[#2457A6] hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Document Vault
          </Link>
          <div className="bg-white border border-red-200 rounded-xl p-6 text-[#B42318]">
            Unable to load document extraction details. It may not exist or you
            may not have access.
          </div>
        </main>
      </div>
    );
  }

  const { document: doc, latest_job: job, pages, observations, classification, security_flags: flags } =
    extraction;
  const activePage = pages[selectedPageIdx] || pages[0] || null;
  const candidates = observations.filter((o) => o.review_status === "candidate");
  const confirmed = observations.filter((o) => o.review_status === "confirmed");

  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033]">
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Back link & Header */}
        <div className="space-y-3">
          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[#2457A6] hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Document Vault
          </Link>

          <div className="bg-white border border-[#E4E7EC] rounded-xl p-6 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <FileText className="w-5 h-5 text-[#2457A6]" />
                <h1 className="text-xl font-bold">{doc.title}</h1>
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-blue-50 text-[#2457A6] border border-blue-200 capitalize">
                  {doc.document_type.replace("_", " ")}
                </span>
                {classification && (
                  <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-slate-100 text-[#475467] border border-slate-200">
                    Detected: {classification.predicted_type.replace("_", " ")} (
                    {Math.round(classification.confidence * 100)}%)
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#667085]">
                <span>File: {doc.original_filename}</span>
                {doc.document_date && <span>Clinical Date: {doc.document_date}</span>}
                {doc.page_count !== null && <span>{doc.page_count} page(s)</span>}
                <span>{extraction.chunks_count} RAG chunk(s)</span>
                {job && (
                  <span>
                    Last Run: <strong className="capitalize">{job.status}</strong> (
                    {job.pipeline_version})
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {!doc.is_archived && (
                <>
                  <button
                    type="button"
                    disabled={processMutation.isPending}
                    onClick={() => processMutation.mutate(pages.length > 0)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold bg-[#2457A6] hover:bg-[#1D4688] text-white disabled:opacity-50 transition-colors shadow-sm"
                  >
                    {processMutation.isPending ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Running OCR &amp; Extraction...
                      </>
                    ) : pages.length > 0 ? (
                      <>
                        <RefreshCw className="w-4 h-4" />
                        Re-analyze Document
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Run Document Analysis
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      window.open(
                        documentsApi.getDownloadUrl(doc.id),
                        "_blank",
                        "noopener,noreferrer"
                      )
                    }
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium border border-[#D0D5DD] bg-white hover:bg-slate-50"
                  >
                    <Download className="w-4 h-4 text-[#2457A6]" />
                    Download
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Status feedback */}
        {statusMsg && (
          <div
            className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm border ${
              statusMsg.type === "success"
                ? "bg-emerald-50 text-[#157A5B] border-emerald-200"
                : "bg-red-50 text-[#B42318] border-red-200"
            }`}
          >
            {statusMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* SEC-011 Prompt Injection Warning */}
        {flags.length > 0 && (
          <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 space-y-1.5">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#946200]">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              Security Notice (SEC-011): Untrusted instruction-like text detected
              and quarantined
            </div>
            <p className="text-xs text-[#946200]">
              {flags.length} suspicious line(s) were isolated from automated
              parsers and future AI retrieval chunks. Legitimate medical values
              were parsed safely.
            </p>
          </div>
        )}

        {/* Two-Pane Inspection Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Left Pane: Extracted Pages */}
          <section className="bg-white border border-[#E4E7EC] rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-[#E4E7EC] flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold">Extracted Document Text</h2>
              {pages.length > 0 && (
                <div className="flex items-center gap-1">
                  {pages.map((p, idx) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setSelectedPageIdx(idx)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                        idx === selectedPageIdx
                          ? "bg-[#2457A6] text-white"
                          : "bg-slate-100 text-[#475467] hover:bg-slate-200"
                      }`}
                    >
                      Page {p.page_number}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {activePage ? (
              <div className="p-5 space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-xs text-[#667085]">
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-[#172033] font-medium">
                    Method: {activePage.extraction_method}
                  </span>
                  {activePage.ocr_confidence !== null && (
                    <span className="px-2 py-0.5 rounded bg-emerald-50 text-[#157A5B] font-medium">
                      Confidence: {Math.round(activePage.ocr_confidence * 100)}%
                    </span>
                  )}
                  <span>{activePage.char_count} characters</span>
                </div>
                <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed bg-[#F7F9FC] border border-[#E4E7EC] rounded-lg p-4 max-h-[540px] overflow-y-auto text-[#172033]">
                  {activePage.raw_text || "(No text extracted on this page)"}
                </pre>
              </div>
            ) : (
              <div className="p-10 text-center space-y-2">
                <Sparkles className="w-8 h-8 text-[#98A2B3] mx-auto" />
                <p className="text-sm font-medium text-[#172033]">
                  Document has not been analyzed yet
                </p>
                <p className="text-xs text-[#667085]">
                  Click &ldquo;Run Document Analysis&rdquo; above to extract text
                  via PyMuPDF / RapidOCR and detect structured medical values.
                </p>
              </div>
            )}
          </section>

          {/* Right Pane: Candidate Observations Review Queue */}
          <section className="bg-white border border-[#E4E7EC] rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-[#E4E7EC] flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold">
                  Extracted Observations Review
                </h2>
                <p className="text-xs text-[#667085]">
                  Review and confirm extracted facts before adding them to your
                  official health history.
                </p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-[#946200] border border-amber-200">
                {candidates.length} pending
              </span>
            </div>

            <div className="p-5 space-y-4">
              {observations.length === 0 ? (
                <p className="text-sm text-[#667085] text-center py-8">
                  {pages.length === 0
                    ? "Run document analysis to extract structured observations."
                    : "No structured lab or vital observations were detected in this document."}
                </p>
              ) : (
                <>
                  {/* Pending Candidates */}
                  {candidates.map((obs) => (
                    <div
                      key={obs.id}
                      className="border border-amber-200 bg-amber-50/30 rounded-xl p-4 space-y-3"
                    >
                      {editingObsId === obs.id ? (
                        <div className="space-y-2.5">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <input
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              placeholder="Test name"
                              className="px-2.5 py-1.5 text-sm border border-[#D0D5DD] rounded-lg bg-white"
                            />
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              placeholder="Value"
                              className="px-2.5 py-1.5 text-sm border border-[#D0D5DD] rounded-lg bg-white"
                            />
                            <input
                              type="text"
                              value={editUnit}
                              onChange={(e) => setEditUnit(e.target.value)}
                              placeholder="Unit (e.g. g/dL)"
                              className="px-2.5 py-1.5 text-sm border border-[#D0D5DD] rounded-lg bg-white"
                            />
                            <input
                              type="text"
                              value={editRange}
                              onChange={(e) => setEditRange(e.target.value)}
                              placeholder="Reference range"
                              className="px-2.5 py-1.5 text-sm border border-[#D0D5DD] rounded-lg bg-white"
                            />
                          </div>
                          <input
                            type="text"
                            value={editReason}
                            onChange={(e) => setEditReason(e.target.value)}
                            placeholder="Optional correction note (saved to audit trail)"
                            className="w-full px-2.5 py-1.5 text-xs border border-[#D0D5DD] rounded-lg bg-white"
                          />
                          <div className="flex items-center gap-2 justify-end">
                            <button
                              type="button"
                              onClick={() => setEditingObsId(null)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border border-[#D0D5DD] bg-white"
                            >
                              <X className="w-3.5 h-3.5" />
                              Cancel
                            </button>
                            <button
                              type="button"
                              disabled={reviewMutation.isPending}
                              onClick={() =>
                                reviewMutation.mutate({
                                  obsId: obs.id,
                                  action: "edit_confirm",
                                  overrides: {
                                    display_name: editName.trim(),
                                    value_raw: editValue.trim(),
                                    unit_raw: editUnit.trim() || null,
                                    reference_range_text: editRange.trim() || null,
                                    reason: editReason.trim() || null,
                                  },
                                })
                              }
                              className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold bg-[#157A5B] text-white hover:bg-emerald-800"
                            >
                              <Check className="w-3.5 h-3.5" />
                              Save &amp; Confirm
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <h3 className="text-sm font-semibold text-[#172033]">
                                {obs.display_name}
                              </h3>
                              <p className="text-base font-bold text-[#2457A6] mt-0.5">
                                {obs.value_raw}{" "}
                                <span className="text-xs font-medium text-[#475467]">
                                  {obs.unit_raw || ""}
                                </span>
                              </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-1.5">
                              {obs.abnormality_flag && (
                                <span
                                  className={`text-xs font-medium px-2 py-0.5 rounded-full border capitalize ${abnormalityBadge(
                                    obs.abnormality_flag
                                  )}`}
                                >
                                  {obs.abnormality_flag}
                                </span>
                              )}
                              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-[#946200] font-medium">
                                Candidate
                              </span>
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#667085]">
                            {obs.reference_range_text && (
                              <span>Ref: {obs.reference_range_text}</span>
                            )}
                            {obs.source_page && <span>Page {obs.source_page}</span>}
                            {obs.extraction_confidence !== null && (
                              <span>
                                Confidence:{" "}
                                {Math.round(obs.extraction_confidence * 100)}%
                              </span>
                            )}
                          </div>

                          <div className="flex flex-wrap items-center gap-2 pt-1">
                            <button
                              type="button"
                              disabled={reviewMutation.isPending}
                              onClick={() =>
                                reviewMutation.mutate({
                                  obsId: obs.id,
                                  action: "confirm",
                                })
                              }
                              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#157A5B] hover:bg-emerald-800 text-white"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Confirm
                            </button>
                            <button
                              type="button"
                              disabled={reviewMutation.isPending}
                              onClick={() => startEditing(obs)}
                              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-[#D0D5DD] bg-white hover:bg-slate-50"
                            >
                              <Pencil className="w-3.5 h-3.5 text-[#2457A6]" />
                              Edit &amp; Confirm
                            </button>
                            <button
                              type="button"
                              disabled={reviewMutation.isPending}
                              onClick={() =>
                                reviewMutation.mutate({
                                  obsId: obs.id,
                                  action: "reject",
                                })
                              }
                              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-red-200 text-[#B42318] bg-white hover:bg-red-50"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              Reject
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}

                  {/* Already Confirmed Observations */}
                  {confirmed.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-[#667085]">
                        Confirmed ({confirmed.length})
                      </h3>
                      {confirmed.map((obs) => (
                        <div
                          key={obs.id}
                          className="border border-emerald-200 bg-emerald-50/40 rounded-lg p-3 flex items-center justify-between gap-3"
                        >
                          <div>
                            <p className="text-sm font-semibold text-[#172033]">
                              {obs.display_name}:{" "}
                              <span className="text-[#157A5B]">
                                {obs.value_raw} {obs.unit_raw || ""}
                              </span>
                            </p>
                            {obs.reference_range_text && (
                              <p className="text-xs text-[#667085]">
                                Ref: {obs.reference_range_text} · Page{" "}
                                {obs.source_page || 1}
                              </p>
                            )}
                          </div>
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-[#157A5B]">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Confirmed
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        </div>

        {/* Phase 5: Local AI Plain-Language Document Summary */}
        {!doc.is_archived && pages.length > 0 && (
          <section className="bg-white border border-[#E4E7EC] rounded-xl shadow-sm p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2 text-[#172033]">
                  <Bot className="w-5 h-5 text-[#2457A6]" />
                  AI Plain-Language Summary (Local Ollama)
                </h2>
                <p className="text-xs text-[#667085] mt-0.5">
                  Explains extracted clinical text in accessible terms using
                  local-first inference. Strictly informational — never diagnoses
                  or prescribes.
                </p>
              </div>
              <button
                type="button"
                disabled={summarizeMutation.isPending}
                onClick={() => summarizeMutation.mutate()}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-[#2457A6] hover:bg-[#1D4688] text-white disabled:opacity-50 shrink-0 transition-colors"
              >
                {summarizeMutation.isPending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Generating Summary...
                  </>
                ) : (
                  <>
                    <BookOpen className="w-3.5 h-3.5" />
                    {aiSummary ? "Regenerate Summary" : "Generate Plain-Language Summary"}
                  </>
                )}
              </button>
            </div>

            {aiError && (
              <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-[#946200] space-y-1">
                <p className="font-semibold">Local AI Unavailable</p>
                <p>{aiError}</p>
                <p className="font-mono text-[11px] text-[#475467]">
                  Tip: Start Ollama locally and run{" "}
                  <code>ollama pull qwen2.5:1.5b</code>
                </p>
              </div>
            )}

            {aiSummary && (
              <div className="space-y-4 border-t border-[#E4E7EC] pt-4">
                <p className="text-sm leading-relaxed text-[#172033]">
                  {aiSummary.summary.plain_language_summary}
                </p>

                {aiSummary.summary.key_findings.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-1.5">
                      Key Points
                    </h3>
                    <ul className="list-disc pl-5 space-y-1 text-sm text-[#172033]">
                      {aiSummary.summary.key_findings.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {aiSummary.summary.medical_terms_explained.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-1.5">
                      Medical Terms Explained
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                      {aiSummary.summary.medical_terms_explained.map((t, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-[#F7F9FC] border border-[#E4E7EC] text-xs"
                        >
                          <p className="font-semibold text-[#2457A6]">
                            {t.term}
                          </p>
                          <p className="text-[#475467] mt-0.5">
                            {t.explanation}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {aiSummary.summary.questions_for_doctor.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-[#667085] mb-1.5">
                      Questions You Might Ask Your Doctor
                    </h3>
                    <ul className="list-disc pl-5 space-y-1 text-sm text-[#172033]">
                      {aiSummary.summary.questions_for_doctor.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#E4E7EC] text-[11px] text-[#667085]">
                  <span>{aiSummary.summary.informational_disclaimer}</span>
                  <span className="font-mono">
                    {aiSummary.provider} · {aiSummary.model} ·{" "}
                    {aiSummary.prompt_id}@{aiSummary.prompt_version} ·{" "}
                    {aiSummary.latency_ms}ms
                  </span>
                </div>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
