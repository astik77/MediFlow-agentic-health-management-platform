export type SafetyLevel =
  | "normal"
  | "boundary_refusal"
  | "emergency_escalation";

export interface CitedRecord {
  entity_type: string;
  entity_id: string;
  label: string;
}

export interface ProposedSymptomAction {
  proposal_type: "symptom";
  status: "pending" | "saved" | "dismissed";
  patient_id: string;
  saved_entity_id?: string;
  payload: {
    name: string;
    severity: "mild" | "moderate" | "severe";
    body_location: string | null;
    frequency: string | null;
    notes: string | null;
  };
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  patient_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  safety_level: SafetyLevel;
  cited_records_json: CitedRecord[] | null;
  clarifying_questions_json: string[] | null;
  proposed_action_json: ProposedSymptomAction | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface ConversationItem {
  id: string;
  patient_id: string;
  title: string;
  status: string;
  is_archived: boolean;
  last_message_at: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  conversation: ConversationItem;
  messages: ConversationMessage[];
}

export interface MessageTurnResponse {
  conversation: ConversationItem;
  user_message: ConversationMessage;
  assistant_message: ConversationMessage;
}
