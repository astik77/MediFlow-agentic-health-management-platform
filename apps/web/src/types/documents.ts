import type { HealthObservation } from "@/types/health";

export type DocumentType =
  | "lab_report"
  | "prescription"
  | "discharge_summary"
  | "imaging"
  | "clinical_note"
  | "insurance"
  | "other";

export type UploadStatus =
  | "pending"
  | "processing"
  | "ready"
  | "failed"
  | "archived";

export type ReviewStatus = "unreviewed" | "reviewed" | "flagged";

export interface DocumentItem {
  id: string;
  patient_id: string;
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  document_type: DocumentType;
  source_type: string;
  upload_status: UploadStatus;
  review_status: ReviewStatus;
  processing_error: string | null;
  title: string;
  description: string | null;
  document_date: string | null;
  page_count: number | null;
  is_archived: boolean;
  uploaded_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface DocumentUploadPayload {
  file: File;
  document_type: DocumentType;
  title?: string;
  description?: string;
  document_date?: string;
}

export interface DocumentUpdatePayload {
  title?: string;
  description?: string | null;
  document_type?: DocumentType;
  document_date?: string | null;
  review_status?: ReviewStatus;
}

export type JobStatus = "queued" | "running" | "completed" | "failed";
export type CandidateReviewAction = "confirm" | "edit_confirm" | "reject";

export interface DocumentPage {
  id: string;
  document_id: string;
  page_number: number;
  extraction_method: string;
  raw_text: string;
  ocr_confidence: number | null;
  char_count: number;
  layout_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  page_start: number;
  page_end: number;
  content: string;
  token_estimate: number;
  section_heading: string | null;
  created_at: string;
}

export interface DocumentProcessingJob {
  id: string;
  document_id: string;
  pipeline_version: string;
  status: JobStatus;
  attempt_count: number;
  error_message: string | null;
  metrics_json: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DocumentClassification {
  predicted_type: DocumentType;
  confidence: number;
  matched_signals: string[];
}

export interface SecurityFlag {
  rule_id: string;
  page_number: number;
  matched_snippet: string;
}

export interface DocumentExtractionResponse {
  document: DocumentItem;
  latest_job: DocumentProcessingJob | null;
  pages: DocumentPage[];
  chunks_count: number;
  chunks: DocumentChunk[];
  observations: HealthObservation[];
  classification: DocumentClassification | null;
  security_flags: SecurityFlag[];
}

export interface CandidateReviewPayload {
  action: CandidateReviewAction;
  display_name?: string;
  value_raw?: string;
  unit_raw?: string | null;
  reference_range_text?: string | null;
  abnormality_flag?: "normal" | "low" | "high" | "critical" | "unknown" | null;
  observed_at?: string | null;
  notes?: string | null;
  reason?: string | null;
}
