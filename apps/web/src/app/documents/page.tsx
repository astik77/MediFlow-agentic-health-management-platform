"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Upload,
  Search,
  Download,
  Pencil,
  Archive,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Calendar,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { useAuth } from "@/features/auth/AuthContext";
import { ApiError, documentsApi } from "@/lib/api";
import type {
  DocumentItem,
  DocumentListResponse,
  DocumentType,
  ReviewStatus,
} from "@/types/documents";

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "lab_report", label: "Lab Report" },
  { value: "prescription", label: "Prescription" },
  { value: "discharge_summary", label: "Discharge Summary" },
  { value: "imaging", label: "Imaging / Scan" },
  { value: "clinical_note", label: "Clinical Note" },
  { value: "insurance", label: "Insurance" },
  { value: "other", label: "Other" },
];

const REVIEW_STATUSES: { value: ReviewStatus; label: string }[] = [
  { value: "unreviewed", label: "Unreviewed" },
  { value: "reviewed", label: "Reviewed" },
  { value: "flagged", label: "Flagged" },
];

const ACCEPTED_MIME_STRING =
  "application/pdf,image/jpeg,image/png,image/webp,image/tiff,.pdf,.jpg,.jpeg,.png,.webp,.tif,.tiff";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDocumentType(type: DocumentType): string {
  const match = DOCUMENT_TYPES.find((t) => t.value === type);
  return match ? match.label : type;
}

function reviewBadgeClass(status: ReviewStatus): string {
  switch (status) {
    case "reviewed":
      return "bg-emerald-50 text-[#157A5B] border-emerald-200";
    case "flagged":
      return "bg-amber-50 text-[#946200] border-amber-200";
    default:
      return "bg-slate-100 text-[#475467] border-slate-200";
  }
}

export default function DocumentsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { authenticated, isLoading: authLoading } = useAuth();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Filters & pagination
  const [filterType, setFilterType] = useState<string>("");
  const [filterReview, setFilterReview] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [includeArchived, setIncludeArchived] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const pageSize = 10;

  // Upload form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [uploadType, setUploadType] = useState<DocumentType>("lab_report");
  const [uploadTitle, setUploadTitle] = useState<string>("");
  const [uploadDescription, setUploadDescription] = useState<string>("");
  const [uploadDate, setUploadDate] = useState<string>("");
  const [uploadFeedback, setUploadFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Edit modal state
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const [editTitle, setEditTitle] = useState<string>("");
  const [editDescription, setEditDescription] = useState<string>("");
  const [editType, setEditType] = useState<DocumentType>("other");
  const [editDate, setEditDate] = useState<string>("");
  const [editReview, setEditReview] = useState<ReviewStatus>("unreviewed");
  const [editError, setEditError] = useState<string | null>(null);

  // Inline archive confirmation state
  const [confirmArchiveId, setConfirmArchiveId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !authenticated) {
      router.replace("/login");
    }
  }, [authenticated, authLoading, router]);

  const { data: docList, isLoading } = useQuery<DocumentListResponse>({
    queryKey: [
      "documents",
      filterType,
      filterReview,
      searchQuery,
      includeArchived,
      page,
    ],
    queryFn: () =>
      documentsApi.list({
        document_type: filterType || undefined,
        review_status: filterReview || undefined,
        q: searchQuery.trim() || undefined,
        include_archived: includeArchived,
        page,
        page_size: pageSize,
      }),
    enabled: authenticated,
  });

  const uploadMutation = useMutation({
    mutationFn: documentsApi.upload,
    onSuccess: (created) => {
      setSelectedFile(null);
      setUploadTitle("");
      setUploadDescription("");
      setUploadDate("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setUploadFeedback({
        type: "success",
        message: `"${created.title}" uploaded and verified (SHA-256 recorded).`,
      });
      setPage(1);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
      queryClient.invalidateQueries({ queryKey: ["health", "overview"] });
    },
    onError: (err: unknown) => {
      const message =
        err instanceof ApiError
          ? err.detail
          : "Upload failed. Please check the file type and size.";
      setUploadFeedback({ type: "error", message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: {
        title?: string;
        description?: string | null;
        document_type?: DocumentType;
        document_date?: string | null;
        review_status?: ReviewStatus;
      };
    }) => documentsApi.update(id, payload),
    onSuccess: () => {
      setEditingDoc(null);
      setEditError(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (err: unknown) => {
      setEditError(
        err instanceof ApiError ? err.detail : "Failed to update document."
      );
    },
  });

  const archiveMutation = useMutation({
    mutationFn: documentsApi.archive,
    onSuccess: () => {
      setConfirmArchiveId(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["timeline"] });
    },
  });

  const handleFileSelected = (file: File | null) => {
    setUploadFeedback(null);
    if (!file) return;
    setSelectedFile(file);
    if (!uploadTitle.trim()) {
      const stripped = file.name.replace(/\.[^.]+$/, "");
      setUploadTitle(stripped);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0] || null;
    handleFileSelected(file);
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadFeedback({
        type: "error",
        message: "Please select a PDF or image file first.",
      });
      return;
    }
    setUploadFeedback(null);
    uploadMutation.mutate({
      file: selectedFile,
      document_type: uploadType,
      title: uploadTitle.trim() || undefined,
      description: uploadDescription.trim() || undefined,
      document_date: uploadDate || undefined,
    });
  };

  const openEditModal = (doc: DocumentItem) => {
    setEditingDoc(doc);
    setEditTitle(doc.title);
    setEditDescription(doc.description || "");
    setEditType(doc.document_type);
    setEditDate(doc.document_date || "");
    setEditReview(doc.review_status);
    setEditError(null);
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingDoc || !editTitle.trim()) return;
    updateMutation.mutate({
      id: editingDoc.id,
      payload: {
        title: editTitle.trim(),
        description: editDescription.trim() || null,
        document_type: editType,
        document_date: editDate || null,
        review_status: editReview,
      },
    });
  };

  const handleDownload = (doc: DocumentItem) => {
    const url = documentsApi.getDownloadUrl(doc.id);
    window.open(url, "_blank", "noopener,noreferrer");
  };

  if (authLoading || !authenticated) {
    return (
      <div className="min-h-screen bg-[#F7F9FC]">
        <Navbar />
        <div className="flex items-center justify-center py-24 text-[#667085] gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
          Loading document vault...
        </div>
      </div>
    );
  }

  const totalPages = docList
    ? Math.max(1, Math.ceil(docList.total / pageSize))
    : 1;

  return (
    <div className="min-h-screen bg-[#F7F9FC] text-[#172033]">
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Header */}
        <section className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
              <FileText className="w-6 h-6 text-[#2457A6]" />
              Medical Document Vault
            </h1>
            <p className="text-sm text-[#475467] mt-1">
              Upload, organize, and securely store your lab reports,
              prescriptions, imaging scans, and discharge summaries.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-medium text-[#157A5B] self-start sm:self-auto">
            <ShieldCheck className="w-4 h-4" />
            Private patient-isolated storage · SHA-256 verified
          </div>
        </section>

        {/* Upload Panel */}
        <section className="bg-white border border-[#E4E7EC] rounded-xl p-6 shadow-sm">
          <h2 className="text-base font-semibold mb-4 flex items-center gap-2">
            <Upload className="w-4 h-4 text-[#2457A6]" />
            Upload Medical Document
          </h2>

          <form onSubmit={handleUploadSubmit} className="space-y-4">
            {/* Drag & drop area */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  fileInputRef.current?.click();
                }
              }}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                isDragging
                  ? "border-[#2457A6] bg-blue-50/70"
                  : "border-[#D0D5DD] hover:border-[#2457A6] hover:bg-slate-50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_MIME_STRING}
                className="hidden"
                onChange={(e) =>
                  handleFileSelected(e.target.files?.[0] || null)
                }
              />
              {selectedFile ? (
                <div className="flex flex-col items-center gap-1">
                  <FileText className="w-8 h-8 text-[#2457A6]" />
                  <p className="text-sm font-semibold text-[#172033]">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-[#667085]">
                    {formatFileSize(selectedFile.size)} · Click or drop another
                    file to replace
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-1.5">
                  <Upload className="w-8 h-8 text-[#667085]" />
                  <p className="text-sm font-medium text-[#172033]">
                    Drag &amp; drop a medical document here, or{" "}
                    <span className="text-[#2457A6] underline">
                      browse files
                    </span>
                  </p>
                  <p className="text-xs text-[#667085]">
                    Supported formats: PDF, JPEG, PNG, WebP, TIFF (max 50 MB)
                  </p>
                </div>
              )}
            </div>

            {/* Metadata inputs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label
                  htmlFor="doc-title"
                  className="block text-xs font-medium text-[#475467] mb-1"
                >
                  Document Title
                </label>
                <input
                  id="doc-title"
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="e.g., Complete Blood Count (Nov 2026)"
                  className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>

              <div>
                <label
                  htmlFor="doc-type"
                  className="block text-xs font-medium text-[#475467] mb-1"
                >
                  Document Category
                </label>
                <select
                  id="doc-type"
                  value={uploadType}
                  onChange={(e) =>
                    setUploadType(e.target.value as DocumentType)
                  }
                  className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                >
                  {DOCUMENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="doc-date"
                  className="block text-xs font-medium text-[#475467] mb-1"
                >
                  Clinical / Report Date (Optional)
                </label>
                <input
                  id="doc-date"
                  type="date"
                  value={uploadDate}
                  onChange={(e) => setUploadDate(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="doc-desc"
                className="block text-xs font-medium text-[#475467] mb-1"
              >
                Notes / Description (Optional)
              </label>
              <input
                id="doc-desc"
                type="text"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                placeholder="Ordering clinic, doctor notes, or context for future reference"
                className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
              />
            </div>

            {uploadFeedback && (
              <div
                className={`flex items-center gap-2 px-3.5 py-2.5 rounded-lg text-sm border ${
                  uploadFeedback.type === "success"
                    ? "bg-emerald-50 text-[#157A5B] border-emerald-200"
                    : "bg-red-50 text-[#B42318] border-red-200"
                }`}
              >
                {uploadFeedback.type === "success" ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0" />
                )}
                <span>{uploadFeedback.message}</span>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!selectedFile || uploadMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-[#2457A6] hover:bg-[#1D4688] text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                {uploadMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Validating &amp; Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Upload Document
                  </>
                )}
              </button>
            </div>
          </form>
        </section>

        {/* Filter & Search Bar */}
        <section className="bg-white border border-[#E4E7EC] rounded-xl p-4 shadow-sm flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#667085] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Search documents by title, filename, or notes..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-[#D0D5DD] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              aria-label="Filter by document category"
              value={filterType}
              onChange={(e) => {
                setFilterType(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg bg-white"
            >
              <option value="">All Categories</option>
              {DOCUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>

            <select
              aria-label="Filter by review status"
              value={filterReview}
              onChange={(e) => {
                setFilterReview(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg bg-white"
            >
              <option value="">All Statuses</option>
              {REVIEW_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>

            <label className="inline-flex items-center gap-1.5 text-xs font-medium text-[#475467] px-2.5 py-2 rounded-lg border border-[#E4E7EC] cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeArchived}
                onChange={(e) => {
                  setIncludeArchived(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-[#D0D5DD] text-[#2457A6]"
              />
              Show Archived
            </label>
          </div>
        </section>

        {/* Document List */}
        <section className="space-y-3">
          <div className="flex items-center justify-between text-xs text-[#667085] px-1">
            <span>
              {docList
                ? `Showing ${docList.items.length} of ${docList.total} document${
                    docList.total === 1 ? "" : "s"
                  }`
                : "Loading documents..."}
            </span>
          </div>

          {isLoading ? (
            <div className="bg-white border border-[#E4E7EC] rounded-xl p-12 text-center text-[#667085] flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-[#2457A6]" />
              Loading your documents...
            </div>
          ) : !docList || docList.items.length === 0 ? (
            <div className="bg-white border border-[#E4E7EC] rounded-xl p-12 text-center">
              <FileText className="w-10 h-10 text-[#98A2B3] mx-auto mb-3" />
              <h3 className="text-base font-semibold text-[#172033]">
                No documents found
              </h3>
              <p className="text-sm text-[#667085] mt-1">
                Upload your first medical report, prescription, or scan above to
                begin building your vault.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {docList.items.map((doc) => (
                <article
                  key={doc.id}
                  className={`bg-white border rounded-xl p-5 shadow-sm transition-colors ${
                    doc.is_archived
                      ? "border-slate-200 bg-slate-50/70 opacity-80"
                      : "border-[#E4E7EC] hover:border-[#2457A6]/40"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="space-y-1.5 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold text-[#172033] truncate">
                          {doc.title}
                        </h3>
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-50 text-[#2457A6] border border-blue-200">
                          {formatDocumentType(doc.document_type)}
                        </span>
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-full border capitalize ${reviewBadgeClass(
                            doc.review_status
                          )}`}
                        >
                          {doc.review_status}
                        </span>
                        {doc.is_archived && (
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-50 text-[#B42318] border border-red-200">
                            Archived
                          </span>
                        )}
                      </div>

                      {doc.description && (
                        <p className="text-sm text-[#475467]">
                          {doc.description}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#667085]">
                        <span>File: {doc.original_filename}</span>
                        <span>{formatFileSize(doc.file_size_bytes)}</span>
                        <span>{doc.mime_type}</span>
                        {doc.document_date && (
                          <span className="inline-flex items-center gap-1 text-[#172033] font-medium">
                            <Calendar className="w-3.5 h-3.5 text-[#2457A6]" />
                            Clinical Date: {doc.document_date}
                          </span>
                        )}
                        <span>
                          Uploaded:{" "}
                          {new Date(doc.uploaded_at).toLocaleDateString()}
                        </span>
                        <span
                          className="font-mono text-[11px] text-[#98A2B3]"
                          title={`SHA-256: ${doc.sha256_hash}`}
                        >
                          SHA-256: {doc.sha256_hash.slice(0, 12)}…
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {!doc.is_archived && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleDownload(doc)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-[#D0D5DD] text-[#172033] hover:bg-slate-50 transition-colors"
                          >
                            <Download className="w-3.5 h-3.5 text-[#2457A6]" />
                            Download
                          </button>

                          <button
                            type="button"
                            onClick={() => openEditModal(doc)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-[#D0D5DD] text-[#172033] hover:bg-slate-50 transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5 text-[#2457A6]" />
                            Edit
                          </button>

                          {confirmArchiveId === doc.id ? (
                            <div className="inline-flex items-center gap-1.5 bg-red-50 border border-red-200 rounded-lg px-2 py-1">
                              <span className="text-xs font-medium text-[#B42318]">
                                Remove file?
                              </span>
                              <button
                                type="button"
                                disabled={archiveMutation.isPending}
                                onClick={() => archiveMutation.mutate(doc.id)}
                                className="px-2 py-0.5 rounded bg-[#B42318] text-white text-xs font-semibold hover:bg-red-800"
                              >
                                Confirm
                              </button>
                              <button
                                type="button"
                                onClick={() => setConfirmArchiveId(null)}
                                className="px-1.5 py-0.5 rounded text-xs text-[#475467] hover:bg-white"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setConfirmArchiveId(doc.id)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-[#E4E7EC] text-[#667085] hover:text-[#B42318] hover:border-red-200 hover:bg-red-50 transition-colors"
                            >
                              <Archive className="w-3.5 h-3.5" />
                              Archive
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}

          {/* Pagination */}
          {docList && docList.total > pageSize && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-xs text-[#667085]">
                Page {page} of {totalPages}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-[#D0D5DD] disabled:opacity-40"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  Previous
                </button>
                <button
                  type="button"
                  disabled={!docList.has_next}
                  onClick={() => setPage((p) => p + 1)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-[#D0D5DD] disabled:opacity-40"
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Edit Metadata Modal */}
      {editingDoc && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-doc-modal-title"
        >
          <div className="bg-white rounded-xl border border-[#E4E7EC] shadow-xl w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2
                id="edit-doc-modal-title"
                className="text-lg font-bold text-[#172033]"
              >
                Edit Document Metadata
              </h2>
              <button
                type="button"
                onClick={() => setEditingDoc(null)}
                className="p-1 rounded-md text-[#667085] hover:bg-slate-100"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="edit-title"
                  className="block text-xs font-medium text-[#475467] mb-1"
                >
                  Title
                </label>
                <input
                  id="edit-title"
                  type="text"
                  required
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2457A6]/30 focus:border-[#2457A6]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="edit-type"
                    className="block text-xs font-medium text-[#475467] mb-1"
                  >
                    Category
                  </label>
                  <select
                    id="edit-type"
                    value={editType}
                    onChange={(e) =>
                      setEditType(e.target.value as DocumentType)
                    }
                    className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg bg-white"
                  >
                    {DOCUMENT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="edit-review"
                    className="block text-xs font-medium text-[#475467] mb-1"
                  >
                    Review Status
                  </label>
                  <select
                    id="edit-review"
                    value={editReview}
                    onChange={(e) =>
                      setEditReview(e.target.value as ReviewStatus)
                    }
                    className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg bg-white"
                  >
                    {REVIEW_STATUSES.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label
                  htmlFor="edit-date"
                  className="block text-xs font-medium text-[#475467] mb-1"
                >
                  Clinical / Report Date
                </label>
                <input
                  id="edit-date"
                  type="date"
                  value={editDate}
                  onChange={(e) => setEditDate(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg"
                />
              </div>

              <div>
                <label
                  htmlFor="edit-desc"
                  className="block text-xs font-medium text-[#475467] mb-1"
                >
                  Description / Notes
                </label>
                <textarea
                  id="edit-desc"
                  rows={3}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-[#D0D5DD] rounded-lg"
                />
              </div>

              {editError && (
                <div className="text-sm text-[#B42318] bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {editError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingDoc(null)}
                  className="px-4 py-2 rounded-lg text-sm font-medium border border-[#D0D5DD] text-[#475467] hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold bg-[#2457A6] hover:bg-[#1D4688] text-white disabled:opacity-50"
                >
                  {updateMutation.isPending && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
