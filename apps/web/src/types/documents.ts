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
