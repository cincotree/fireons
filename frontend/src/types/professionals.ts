export interface NriSummary {
  confidence: "high" | "medium" | "low";
  signal_count: number;
  confirmed: boolean;
  website_url: string | null;
}

export interface NriSignal {
  id: string;
  page_url: string;
  signal_type: string;
  matched_text: string;
  location: string;
  confidence: "high" | "medium" | "low";
  review_status: "pending" | "confirmed" | "rejected";
  last_seen_at: string;
}

export interface NriWebsite {
  url: string;
  domain: string;
  derived_from: string;
  check_status: string;
  pages_checked: number;
  last_checked_at: string | null;
}

export interface NriDetail {
  registration_id: string;
  website: NriWebsite | null;
  signals: NriSignal[];
}

export interface Registration {
  id: string;
  professional_id: string;
  name: string;
  kind: string;
  registration_number: string;
  profession_type: string;
  source_key: string;
  source_name: string;
  regulator: string;
  status: "active" | "expired" | "delisted";
  valid_from: string | null;
  valid_until: string | null;
  validity_raw: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  address: string | null;
  email: string | null;
  phone: string | null;
  contact_person: string | null;
  source_url: string;
  first_seen_at: string;
  last_seen_at: string;
  last_changed_at: string;
  nri: NriSummary | null;
}

export interface RegistrationPage {
  items: Registration[];
  total: number;
  page: number;
  page_size: number;
}

export interface RunInfo {
  status: string;
  started_at: string;
  finished_at: string | null;
  records_seen: number;
  expected_total: number | null;
}

export interface ProfessionalSource {
  key: string;
  name: string;
  regulator: string;
  profession_type: string;
  total_registrations: number;
  last_run: RunInfo | null;
  last_success_at: string | null;
}

export interface Facets {
  states: string[];
  cities: string[];
  profession_types: string[];
}

export interface FieldChange {
  field: string;
  previous: unknown;
  current: unknown;
}

export interface RegistrationVersion {
  id: string;
  scraped_at: string;
  content_hash: string;
  is_initial: boolean;
  changes: FieldChange[];
  snapshot: Record<string, unknown>;
}

export interface RegistrationHistory {
  registration_id: string;
  versions: RegistrationVersion[];
}
