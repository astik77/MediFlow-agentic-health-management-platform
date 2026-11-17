export interface MedicalTermExplanation {
  term: string;
  explanation: string;
}

export interface DocumentSummaryOutput {
  patient_id: string;
  plain_language_summary: string;
  key_findings: string[];
  medical_terms_explained: MedicalTermExplanation[];
  questions_for_doctor: string[];
  informational_disclaimer: string;
}

export interface DocumentSummaryApiResponse {
  document_id: string;
  provider: string;
  model: string;
  prompt_id: string;
  prompt_version: string;
  latency_ms: number;
  attempts: number;
  summary: DocumentSummaryOutput;
  generated_at: string;
}

export interface ProviderHealthResponse {
  provider: string;
  is_local: boolean;
  available: boolean;
  default_model: string;
  installed_models: string[];
  detail: string | null;
}

export interface PrivacyPolicyStatusResponse {
  local_first: boolean;
  external_ai_enabled: boolean;
  allow_external_ai_for_real_data: boolean;
  external_ai_synthetic_only: boolean;
}

export interface PromptRegistryItem {
  prompt_id: string;
  version: string;
  task_type: string;
  description: string;
  sha256: string;
}

export interface AIStatusResponse {
  default_provider: string;
  default_model: string;
  embedding_model: string;
  recommended_local_models: string[];
  privacy_policy: PrivacyPolicyStatusResponse;
  providers: ProviderHealthResponse[];
  prompt_registry: PromptRegistryItem[];
}

export interface RagSearchHit {
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_type: string;
  document_date: string | null;
  page_start: number;
  page_end: number;
  section_heading: string | null;
  snippet: string;
  score: number;
  lexical_score: number;
  vector_score: number;
  match_type: string;
}

export interface RagSearchResponse {
  query: string;
  embedding_model: string;
  total_hits: number;
  hits: RagSearchHit[];
}

export interface RagReindexResponse {
  documents_indexed: number;
  chunks_indexed: number;
  embedding_model: string;
  dimensions: number;
}
