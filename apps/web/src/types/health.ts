export type SourceType =
  | "patient_reported"
  | "document_extracted"
  | "patient_confirmed"
  | "ai_proposed";

export type ReviewStatus = "confirmed" | "candidate" | "rejected" | "uncertain";

export interface PatientCondition {
  id: string;
  patient_id: string;
  name: string;
  status: "active" | "resolved" | "remission" | "inactive";
  severity: string | null;
  onset_date: string | null;
  resolved_date: string | null;
  notes: string | null;
  source_type: SourceType;
  review_status: ReviewStatus;
  source_document_id: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface PatientAllergy {
  id: string;
  patient_id: string;
  allergen: string;
  category: "medication" | "food" | "environmental" | "other";
  reaction: string | null;
  severity: "mild" | "moderate" | "severe" | "life_threatening";
  status: "active" | "inactive" | "resolved";
  onset_date: string | null;
  notes: string | null;
  source_type: SourceType;
  review_status: ReviewStatus;
  source_document_id: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface PatientSymptom {
  id: string;
  patient_id: string;
  name: string;
  severity: "mild" | "moderate" | "severe";
  frequency: string | null;
  body_location: string | null;
  status: "ongoing" | "resolved" | "intermittent";
  started_at: string;
  ended_at: string | null;
  notes: string | null;
  source_type: SourceType;
  review_status: ReviewStatus;
  source_document_id: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface HealthObservation {
  id: string;
  patient_id: string;
  observation_type: "lab_result" | "vital_sign" | "measurement" | "clinical_note";
  display_name: string;
  value_raw: string;
  unit_raw: string | null;
  value_numeric: number | null;
  value_normalized: number | null;
  unit_normalized: string | null;
  reference_range_text: string | null;
  abnormality_flag: "normal" | "low" | "high" | "critical" | "unknown" | null;
  observed_at: string;
  notes: string | null;
  source_type: SourceType;
  review_status: ReviewStatus;
  source_document_id: string | null;
  source_page: number | null;
  extraction_method: string | null;
  extraction_confidence: number | null;
  provenance_metadata: Record<string, unknown> | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecordRevision {
  id: string;
  patient_id: string;
  entity_type: "condition" | "allergy" | "symptom" | "observation";
  entity_id: string;
  revision_number: number;
  action: "created" | "corrected" | "archived";
  previous_data: Record<string, unknown> | null;
  new_data: Record<string, unknown>;
  reason: string | null;
  changed_by_user_id: string;
  created_at: string;
}

export interface HealthEvent {
  id: string;
  patient_id: string;
  event_category:
    | "symptom"
    | "condition"
    | "allergy"
    | "observation"
    | "document"
    | "correction"
    | "summary"
    | "general";
  title: string;
  summary: string | null;
  event_occurred_at: string;
  source_type: SourceType;
  review_status: ReviewStatus;
  related_entity_type: string | null;
  related_entity_id: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface TimelineResponse {
  items: HealthEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface HealthOverview {
  conditions_count: number;
  active_conditions_count: number;
  allergies_count: number;
  symptoms_count: number;
  ongoing_symptoms_count: number;
  observations_count: number;
  timeline_events_count: number;
  recent_events: HealthEvent[];
}
