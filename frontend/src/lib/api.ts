// API client for the CMMC compliance backend

const BASE_URL = import.meta.env.VITE_API_URL || '/api';

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}

// Controls
export const api = {
  // ─── Controls ──────────────────────────────────────────────────────────────
  getControls: (params?: { level?: string; domain?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.level) q.set('level', params.level);
    if (params?.domain) q.set('domain', params.domain);
    if (params?.status) q.set('status', params.status);
    return fetchJSON<import('../types/api').ControlListResponse>(`/controls/?${q}`);
  },

  getControl: (id: string) =>
    fetchJSON<import('../types/api').ControlResponse>(`/controls/${id}`),

  updateControl: (id: string, body: object) =>
    fetchJSON<import('../types/api').ControlResponse>(`/controls/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  // ─── Assessment ────────────────────────────────────────────────────────────
  getDashboard: () =>
    fetchJSON<import('../types/api').DashboardSummary>('/assessment/dashboard'),

  getSPRS: () =>
    fetchJSON<import('../types/api').SPRSResult>('/assessment/sprs'),

  // ─── Blockchain ────────────────────────────────────────────────────────────
  getBlockchainStatus: () =>
    fetchJSON<import('../types/api').BlockchainStatusResponse>('/blockchain/status'),

  getAuditTrail: (limit = 50, offset = 0, tx_type?: string) => {
    const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (tx_type) q.set('tx_type', tx_type);
    return fetchJSON<import('../types/api').AuditTrailResponse>(`/blockchain/audit-trail?${q}`);
  },

  getSPRSHistory: () =>
    fetchJSON<import('../types/api').SPRSHistoryResponse>('/blockchain/sprs/history'),

  getAttestationHistory: (controlId: string) =>
    fetchJSON<import('../types/api').AttestationHistoryResponse>(`/blockchain/attest/${controlId}/history`),

  verifyAttestation: (controlId: string) =>
    fetchJSON<import('../types/api').AttestationVerifyResponse>(`/blockchain/attest/${controlId}/verify`),

  submitAttestation: (controlId: string, body: object) =>
    fetchJSON<import('../types/api').AttestationResponse>(`/blockchain/attest/${controlId}`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  anchorSPRS: (body: object) =>
    fetchJSON<import('../types/api').SPRSAnchorResponse>('/blockchain/sprs/anchor', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  registerEvidence: (evidenceId: string) =>
    fetch(`${BASE_URL}/blockchain/evidence/${evidenceId}/register`, { method: 'POST' })
      .then(r => r.json()),

  getLedgerIntegrity: () =>
    fetchJSON<import('../types/api').LedgerIntegrityResponse>('/blockchain/integrity'),
};
