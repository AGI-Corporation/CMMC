import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { ShieldCheck, ChevronRight, CheckCircle2, Link2 } from 'lucide-react';

const STATUSES = [
  { value: 'implemented', label: 'Implemented' },
  { value: 'partially_implemented', label: 'Partially Implemented' },
  { value: 'planned', label: 'Planned' },
  { value: 'not_implemented', label: 'Not Implemented' },
];

export default function AttestationWizard() {
  const qc = useQueryClient();
  const [step, setStep] = useState<'select' | 'form' | 'done'>('select');
  const [selectedId, setSelectedId] = useState('');
  const [status, setStatus] = useState('implemented');
  const [confidence, setConfidence] = useState(0.8);
  const [notes, setNotes] = useState('');
  const [txResult, setTxResult] = useState<{ tx_id: string; block_height: number; payload_hash: string } | null>(null);

  const { data: controls, isLoading: ctrlLoading } = useQuery({
    queryKey: ['controls'],
    queryFn: () => api.getControls(),
  });

  const attestMutation = useMutation({
    mutationFn: (body: object) => api.submitAttestation(selectedId, body),
    onSuccess: (data) => {
      setTxResult({ tx_id: data.tx_id, block_height: data.block_height, payload_hash: data.payload_hash });
      setStep('done');
      qc.invalidateQueries({ queryKey: ['audit-trail'] });
      qc.invalidateQueries({ queryKey: ['blockchain-status'] });
    },
  });

  const sprsAnchorMutation = useMutation({
    mutationFn: () =>
      api.getSPRS().then(sprs =>
        api.anchorSPRS({
          sprs_score: sprs.sprs_score,
          total_controls: sprs.controls_assessed,
          implemented: sprs.controls_implemented,
          attestation_ids: [],
          notes: `Anchored after attestation of ${selectedId}`,
        })
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sprs-history'] });
    },
  });

  const handleSubmit = () => {
    attestMutation.mutate({ status, confidence, notes, evidence_hashes: [] });
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Attestation Wizard</h1>
        <p className="text-gray-400 text-sm mt-1">
          Immutably record a control's compliance status on the cmmc.blockchain ledger
        </p>
      </div>

      {/* Progress steps */}
      <div className="flex items-center gap-2 text-sm">
        {(['select', 'form', 'done'] as const).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border ${
              step === s
                ? 'bg-violet-700 border-violet-500 text-white'
                : ['form', 'done'].includes(step) && i < ['select', 'form', 'done'].indexOf(step)
                ? 'bg-emerald-700 border-emerald-500 text-white'
                : 'bg-gray-800 border-gray-700 text-gray-500'
            }`}>{i + 1}</div>
            <span className={step === s ? 'text-gray-200' : 'text-gray-500'}>
              {['Select Control', 'Sign & Attest', 'Confirmed'][i]}
            </span>
            {i < 2 && <ChevronRight className="w-4 h-4 text-gray-700" />}
          </div>
        ))}
      </div>

      {/* Step 1: Select control */}
      {step === 'select' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-200">Select a CMMC Control to Attest</h2>
          {ctrlLoading ? (
            <div className="text-gray-500 text-sm">Loading controls…</div>
          ) : (
            <select
              value={selectedId}
              onChange={e => setSelectedId(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-gray-200 focus:outline-none focus:border-violet-600"
            >
              <option value="">— Choose a control —</option>
              {controls?.controls.map(cr => (
                <option key={cr.control.id} value={cr.control.id}>
                  {cr.control.id} — {cr.control.title}
                </option>
              ))}
            </select>
          )}
          <button
            disabled={!selectedId}
            onClick={() => setStep('form')}
            className="w-full py-2.5 rounded-lg bg-violet-700 hover:bg-violet-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium transition-colors"
          >
            Continue
          </button>
        </div>
      )}

      {/* Step 2: Form */}
      {step === 'form' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-5">
          <h2 className="text-lg font-semibold text-gray-200">
            Attest: <code className="text-violet-400 text-base">{selectedId}</code>
          </h2>

          <div>
            <label className="text-sm text-gray-400 block mb-1.5">Implementation Status</label>
            <select
              value={status}
              onChange={e => setStatus(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-gray-200 focus:outline-none focus:border-violet-600"
            >
              {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>

          <div>
            <label className="text-sm text-gray-400 block mb-1.5">
              Zero Trust Confidence Score: <span className="text-violet-400 font-bold">{Math.round(confidence * 100)}%</span>
            </label>
            <input
              type="range" min={0} max={1} step={0.01}
              value={confidence}
              onChange={e => setConfidence(Number(e.target.value))}
              className="w-full accent-violet-600"
            />
            <div className="flex justify-between text-xs text-gray-600 mt-1">
              <span>0% — Unverified</span>
              <span>100% — Fully verified</span>
            </div>
          </div>

          <div>
            <label className="text-sm text-gray-400 block mb-1.5">Notes / Evidence Summary</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              placeholder="Describe the evidence and how this control is implemented…"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-600 resize-none"
            />
          </div>

          <div className="bg-gray-950 rounded-lg px-4 py-3 text-xs text-gray-500 border border-gray-800">
            <ShieldCheck className="w-4 h-4 inline mr-1.5 text-violet-500" />
            This attestation will be cryptographically signed and written to the immutable blockchain ledger.
            No CUI content is stored on-chain — only a SHA-256 hash and metadata.
          </div>

          {attestMutation.error && (
            <div className="bg-red-900/20 border border-red-800 rounded-lg px-4 py-3 text-sm text-red-300">
              {String(attestMutation.error)}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => setStep('select')}
              className="flex-1 py-2.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={attestMutation.isPending}
              className="flex-1 py-2.5 rounded-lg bg-violet-700 hover:bg-violet-600 disabled:opacity-40 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2"
            >
              {attestMutation.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Submitting…
                </>
              ) : (
                <>
                  <Link2 className="w-4 h-4" />
                  Submit On-Chain
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Done */}
      {step === 'done' && txResult && (
        <div className="bg-gray-900 border border-emerald-800 rounded-xl p-6 space-y-5">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />
            <div>
              <h2 className="text-lg font-semibold text-white">Attestation Confirmed</h2>
              <p className="text-gray-400 text-sm">Written to block #{txResult.block_height}</p>
            </div>
          </div>
          <div className="space-y-3 text-xs">
            <div>
              <div className="text-gray-500 mb-1">Transaction ID</div>
              <code className="text-emerald-400 break-all">{txResult.tx_id}</code>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Payload Hash (SHA-256)</div>
              <code className="text-gray-300 break-all">{txResult.payload_hash}</code>
            </div>
          </div>

          {/* Optionally anchor SPRS */}
          {!sprsAnchorMutation.isSuccess && (
            <button
              onClick={() => sprsAnchorMutation.mutate()}
              disabled={sprsAnchorMutation.isPending}
              className="w-full py-2.5 rounded-lg bg-blue-800 hover:bg-blue-700 disabled:opacity-40 text-white text-sm font-medium transition-colors"
            >
              {sprsAnchorMutation.isPending ? 'Anchoring SPRS…' : 'Also Anchor Current SPRS Score On-Chain'}
            </button>
          )}
          {sprsAnchorMutation.isSuccess && (
            <div className="flex items-center gap-2 text-emerald-400 text-sm">
              <CheckCircle2 className="w-4 h-4" /> SPRS score anchored on-chain
            </div>
          )}

          <button
            onClick={() => { setStep('select'); setSelectedId(''); setTxResult(null); attestMutation.reset(); sprsAnchorMutation.reset(); }}
            className="w-full py-2.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition-colors"
          >
            Attest Another Control
          </button>
        </div>
      )}
    </div>
  );
}
