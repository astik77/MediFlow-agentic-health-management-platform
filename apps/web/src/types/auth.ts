export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface AuthStatus {
  authenticated: boolean;
  user: User | null;
  patient_id: string | null;
  is_onboarded: boolean;
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone_number: string;
}

export interface MedicalBaseline {
  existing_conditions?: string[];
  known_allergies?: string[];
  [key: string]: unknown;
}

export interface PatientProfile {
  id: string;
  user_id: string;
  full_name: string;
  date_of_birth: string | null;
  biological_sex: string | null;
  blood_group: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  emergency_contact: EmergencyContact | null;
  medical_baseline: MedicalBaseline | null;
  is_onboarded: boolean;
  created_at: string;
  updated_at: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  date_of_birth?: string | null;
  biological_sex?: string | null;
  blood_group?: string | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  emergency_contact?: EmergencyContact | null;
  medical_baseline?: MedicalBaseline | null;
}

export interface OnboardingPayload {
  date_of_birth?: string | null;
  biological_sex?: string | null;
  blood_group?: string | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  emergency_contact?: EmergencyContact | null;
  existing_conditions?: string[];
  known_allergies?: string[];
}
