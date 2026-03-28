// API types matching the FastAPI backend models

export interface Control {
  id: string;
  title: string;
  description: string;
  domain: string;
  level: string;
  nist_mapping: string | null;
  weight: number;
}

export interface ControlResponse {
  control: Control;
  implementation_status: string | null;
  evidence_count: number;
  notes: string | null;
  confidence: number;
  poam_required: boolean;
}

export interface ControlListResponse {
  controls: ControlResponse[];
  total: number;
}

export interface DashboardSummary {
  total_controls: number;
  implemented: number;
  not_implemented: number;
  partially_implemented: number;
  not_started: number;
  not_applicable: number;
  compliance_percentage: number;
  sprs_score: number;
  by_domain: Record<string, { total: number; implemented: number; not_implemented: number }>;
  by_level: Record<string, { total: number; implemented: number }>;
  readiness: string;
}

export interface SPRSResult {
  organization: string;
  system_name: string;
  sprs_score: number;
  max_score: number;
  controls_assessed: number;
  controls_implemented: number;
  controls_not_implemented: number;
  deductions: Array<{ control_id: string; deduction: number }>;
  certification_level: string;
  assessment_date: string;
}

// Blockchain types
export interface BlockchainTx {
  id: string;
  tx_type: 'attestation' | 'sprs_anchor' | 'evidence' | 'assessment';
  org_id: string;
  control_id: string | null;
  evidence_id: string | null;
  payload_hash: string;
  previous_tx_hash: string | null;
  block_height: number;
  status: 'pending' | 'confirmed' | 'failed';
  payload: Record<string, unknown>;
  created_at: string;
  confirmed_at: string | null;
}

export interface AttestationResponse {
  attestation_id: string;
  control_id: string;
  tx_id: string;
  block_height: number;
  payload_hash: string;
  status: string;
  confidence: number;
  evidence_hashes: string[];
  org_id: string;
  assessor_id: string | null;
  timestamp: string;
  previous_tx_hash: string | null;
}

export interface AttestationHistoryResponse {
  control_id: string;
  org_id: string;
  total_records: number;
  attestations: AttestationResponse[];
}

export interface SPRSAnchorResponse {
  anchor_id: string;
  tx_id: string;
  block_height: number;
  payload_hash: string;
  sprs_score: number;
  total_controls: number;
  implemented: number;
  org_id: string;
  timestamp: string;
}

export interface SPRSHistoryResponse {
  org_id: string;
  total_anchors: number;
  anchors: SPRSAnchorResponse[];
}

export interface AuditTrailResponse {
  org_id: string;
  total_transactions: number;
  transactions: BlockchainTx[];
}

export interface BlockchainStatusResponse {
  connected: boolean;
  ledger_mode: string;
  latest_block_height: number;
  total_transactions: number;
  org_id: string;
  chain_id: string;
}

export interface LedgerIntegrityResponse {
  blocks_checked: number;
  issues_found: number;
  chain_valid: boolean;
  issues: string[];
}

export interface AttestationVerifyResponse {
  control_id: string;
  verified: boolean;
  db_status: string | null;
  chain_status: string | null;
  db_confidence: number | null;
  chain_confidence: number | null;
  discrepancy: boolean;
  last_tx_id: string | null;
  last_block_height: number | null;
  message: string;
}
