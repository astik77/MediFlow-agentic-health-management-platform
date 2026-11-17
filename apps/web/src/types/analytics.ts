export type TrendDirection =
  | "increasing"
  | "decreasing"
  | "stable"
  | "insufficient_data";

export type TrendWindow = "30d" | "90d" | "1y" | "all";

export type SummaryGenerationMode = "local_ai" | "deterministic_fallback";

export interface TrendDataPoint {
  observation_id: string;
  observed_at: string;
  value: number;
  unit: string | null;
  value_raw: string;
  unit_raw: string | null;
  reference_range_text: string | null;
  abnormality_flag: string | null;
  source_document_id: string | null;
}

export interface BiomarkerTrendSeries {
  biomarker_key: string;
  display_name: string;
  unit: string | null;
  observation_type: string;
  point_count: number;
  latest_value: number;
  latest_observed_at: string;
  latest_abnormality_flag: string | null;
  previous_value: number | null;
  delta_absolute: number | null;
  delta_percent: number | null;
  direction: TrendDirection;
  min_value: number;
  max_value: number;
  mean_value: number;
  reference_low: number | null;
  reference_high: number | null;
  reference_range_text: string | null;
  points: TrendDataPoint[];
}

export interface BiomarkerTrendsResponse {
  window: TrendWindow;
  biomarker_filter: string | null;
  series_count: number;
  series: BiomarkerTrendSeries[];
}

export interface DashboardKPIs {
  active_conditions_count: number;
  active_allergies_count: number;
  ongoing_symptoms_count: number;
  confirmed_observations_count: number;
  abnormal_observations_count: number;
  documents_count: number;
  pending_candidates_count: number;
  pending_symptom_proposals_count: number;
}

export interface AbnormalObservationAlert {
  id: string;
  display_name: string;
  value_raw: string;
  unit_raw: string | null;
  reference_range_text: string | null;
  abnormality_flag: string;
  observed_at: string;
  source_document_id: string | null;
}

export interface PendingReviewItem {
  document_id: string;
  document_title: string;
  document_type: string;
  pending_count: number;
  uploaded_at: string;
}

export interface AvailableBiomarkerItem {
  biomarker_key: string;
  display_name: string;
  unit: string | null;
  point_count: number;
  latest_value: number;
  latest_abnormality_flag: string | null;
  direction: TrendDirection;
}

export interface HealthSummaryMetricsSnapshot {
  observations_in_window: number;
  abnormal_observations_in_window: number;
  symptoms_logged_in_window: number;
  ongoing_symptoms_total: number;
  documents_uploaded_in_window: number;
  active_conditions_total: number;
  pending_candidates_excluded: number;
}

export interface NotableTrendItem {
  biomarker: string;
  latest_value: number;
  unit: string | null;
  direction: TrendDirection;
  delta_percent: number | null;
  abnormality_flag: string | null;
  reference_range_text: string | null;
}

export interface HealthSummaryItem {
  id: string;
  window_days: number;
  period_start: string;
  period_end: string;
  headline: string;
  summary_text: string;
  highlights: string[];
  notable_trends: NotableTrendItem[];
  questions_for_doctor: string[];
  metrics_snapshot: HealthSummaryMetricsSnapshot;
  generation_mode: SummaryGenerationMode;
  model_name: string | null;
  prompt_version: string | null;
  informational_disclaimer: string;
  created_at: string;
}

export interface HealthSummaryListResponse {
  items: HealthSummaryItem[];
  total: number;
}

export interface DashboardResponse {
  kpis: DashboardKPIs;
  recent_abnormal_observations: AbnormalObservationAlert[];
  pending_review_documents: PendingReviewItem[];
  available_biomarkers: AvailableBiomarkerItem[];
  latest_summary: HealthSummaryItem | null;
  generated_at: string;
}
