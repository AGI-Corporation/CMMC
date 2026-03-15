
export interface Control {
  id: string;
  title: string;
  description: string;
  domain: string;
  level: string;
  nist_mapping?: string;
  weight: number;
}

export interface ControlResponse {
  control: Control;
  implementation_status: string;
  evidence_count: number;
  notes?: string;
  confidence: number;
  poam_required: boolean;
}

export interface DashboardSummary {
  total_controls: number;
  implemented: number;
  not_implemented: number;
  partially_implemented: number;
  not_started: number;
  compliance_percentage: number;
  sprs_score: number;
  by_domain: Record<string, any>;
  by_level: Record<string, any>;
  readiness: string;
}

export interface ZTPillarScore {
  pillar: string;
  total_controls: number;
  implemented: number;
  partial: number;
  not_implemented: number;
  maturity_pct: number;
  confidence_avg: number;
}
