import React, { useState, useCallback } from 'react';
import { X, Edit3, Search, Loader2, CheckCircle2, AlertTriangle, HelpCircle, XCircle } from 'lucide-react';
import { Button } from '../common/Button';
import { useTranslation } from '../../i18n/LanguageContext';
import { medicinesApi } from '../../api/medicines';
import { verificationApi } from '../../api/verification';

// Status display helpers
const STATUS_CONFIG = {
  'Matches a catalogue record': {
    icon: CheckCircle2,
    color: 'var(--color-success)',
    bg: 'var(--color-success-bg)',
    border: 'var(--color-success-border)',
    label: 'Matches a catalogue record',
  },
  VERIFIED: {
    icon: CheckCircle2,
    color: 'var(--color-success)',
    bg: 'var(--color-success-bg)',
    border: 'var(--color-success-border)',
    label: 'Matches a catalogue record',
  },
  'Regulatory alert found': {
    icon: XCircle,
    color: 'var(--color-danger)',
    bg: 'var(--color-danger-bg)',
    border: 'var(--color-danger-border)',
    label: 'Regulatory alert found',
  },
  HIGH_RISK: {
    icon: XCircle,
    color: 'var(--color-danger)',
    bg: 'var(--color-danger-bg)',
    border: 'var(--color-danger-border)',
    label: 'Regulatory alert found',
  },
  'Needs verification': {
    icon: AlertTriangle,
    color: 'var(--color-warning)',
    bg: 'var(--color-warning-bg)',
    border: 'var(--color-warning-border)',
    label: 'Needs verification',
  },
  NEEDS_VERIFICATION: {
    icon: AlertTriangle,
    color: 'var(--color-warning)',
    bg: 'var(--color-warning-bg)',
    border: 'var(--color-warning-border)',
    label: 'Needs verification',
  },
  'No matching record in the MedSure catalogue': {
    icon: HelpCircle,
    color: 'var(--color-text-subtle)',
    bg: 'var(--color-bg-subtle)',
    border: 'var(--color-border)',
    label: 'No matching record in the MedSure catalogue',
  },
  NO_MATCH: {
    icon: HelpCircle,
    color: 'var(--color-text-subtle)',
    bg: 'var(--color-bg-subtle)',
    border: 'var(--color-border)',
    label: 'No matching record in the MedSure catalogue',
  },
  'Insufficient input': {
    icon: HelpCircle,
    color: 'var(--color-text-subtle)',
    bg: 'var(--color-bg-subtle)',
    border: 'var(--color-border)',
    label: 'Insufficient data',
  },
};

export const ManualEntryModal = ({ isOpen, onClose, onSubmit, loading }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    brand_name: '',
    generic_name: '',
    strength: '',
    manufacturer: '',
    batch_number: '',
    expiry_date: '',
    mrp: '',
    barcode: '',
  });

  const [phase, setPhase] = useState('form'); // 'form' | 'searching' | 'result'
  const [searchResult, setSearchResult] = useState(null);
  const [searchError, setSearchError] = useState(null);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleScreening = async (e) => {
    e.preventDefault();
    if (!formData.brand_name.trim() && !formData.barcode.trim() && !formData.generic_name.trim()) {
      alert('Please enter at least a Brand Name, Generic Name, or Barcode/GTIN.');
      return;
    }

    setPhase('searching');
    setSearchError(null);
    setSearchResult(null);

    try {
      // Always call /api/scan/analyze — it handles barcode exact match, fuzzy name match,
      // batch-level regulatory alert detection, and risk assessment in one shot.
      const extracted_fields = {
        brand_name: formData.brand_name.trim() || undefined,
        generic_name: formData.generic_name.trim() || undefined,
        strength: formData.strength.trim() || undefined,
        manufacturer: formData.manufacturer.trim() || undefined,
        batch_number: formData.batch_number.trim() || undefined,
        expiry_date: formData.expiry_date.trim() || undefined,
        mrp: formData.mrp ? parseFloat(formData.mrp) : undefined,
      };

      const res = await verificationApi.analyzeScan({
        barcode: formData.barcode.trim() || null,
        extracted_fields,
      });

      // Map ScanAnalyzeResponse to our result shape
      const firstMed = res.matched_medicines?.[0] || null;
      const recommendation = res.risk_assessment?.recommendation || 'NO_MATCH';
      const confidence = firstMed?.confidence_score ?? 0;

      setSearchResult({
        status: recommendation,
        confidence,
        medicine: firstMed ? {
          medicine_id: firstMed.medicine_id,
          brand_name: firstMed.brand_name,
          generic_name: firstMed.generic_name,
          strength: firstMed.strength,
          dosage_form: firstMed.dosage_form,
          manufacturer: firstMed.manufacturer,
          mrp: firstMed.mrp,
          ceiling_price: firstMed.ceiling_price,
          source: firstMed.source,
          match_flags: firstMed.match_flags,
        } : null,
        risk_assessment: res.risk_assessment,
        regulatory_alerts: res.regulatory_alerts || [],
        evidence_links: res.evidence_links || [],
        per_layer_results: res.per_layer_results,
      });
      setPhase('result');
    } catch (err) {
      console.error('Manual screening error:', err);
      setSearchError(err.message || 'Unable to reach MedSure backend. Please check your connection.');
      setPhase('form');
    }
  };

  const handleConfirmSubmit = () => {
    onSubmit({
      ...formData,
      mrp: formData.mrp ? parseFloat(formData.mrp) : undefined,
      _verifyResult: searchResult,
    });
    setPhase('form');
    setSearchResult(null);
  };

  const handleReset = () => {
    setPhase('form');
    setSearchResult(null);
    setSearchError(null);
  };

  const resultConfig = searchResult ? (STATUS_CONFIG[searchResult.status] || STATUS_CONFIG.NEEDS_VERIFICATION) : null;

  return (
    <div className="modal-overlay" onClick={phase === 'form' ? onClose : undefined} role="dialog" aria-modal="true">
      <div className="modal-content" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Edit3 size={20} style={{ color: 'var(--color-primary)' }} />
            <h2 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.25rem' }}>
              {phase === 'result' ? 'Screening Result' : 'Manual Details Entry'}
            </h2>
          </div>
          <button onClick={phase === 'form' ? onClose : handleReset} aria-label="Close" style={{ padding: '0.375rem', borderRadius: '50%' }}>
            <X size={20} />
          </button>
        </div>

        {/* Phase: Form */}
        {phase === 'form' && (
          <form onSubmit={handleScreening}>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                Enter information from the medicine packaging to screen against the master catalogue.
                For fastest results, provide a <strong>barcode/GTIN</strong> number.
              </p>

              {searchError && (
                <div style={{ backgroundColor: 'var(--color-danger-bg)', border: '1px solid var(--color-danger-border)', borderRadius: 'var(--radius-md)', padding: '0.75rem', fontSize: '0.8125rem', color: 'var(--color-danger)' }}>
                  ⚠ {searchError}
                </div>
              )}

              <div className="form-group">
                <label className="form-label" htmlFor="manual-brand">Brand Name *</label>
                <input
                  id="manual-brand"
                  name="brand_name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Dolo 650, Crocin, Augmentin"
                  value={formData.brand_name}
                  onChange={handleChange}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="manual-generic">Generic / Salt Name</label>
                <input
                  id="manual-generic"
                  name="generic_name"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Paracetamol, Amoxicillin"
                  value={formData.generic_name}
                  onChange={handleChange}
                />
              </div>

              <div className="grid-2" style={{ gap: '0.75rem' }}>
                <div className="form-group">
                  <label className="form-label" htmlFor="manual-strength">Strength</label>
                  <input id="manual-strength" name="strength" type="text" className="form-input"
                    placeholder="e.g. 650mg, 500mg" value={formData.strength} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="manual-manufacturer">Manufacturer</label>
                  <input id="manual-manufacturer" name="manufacturer" type="text" className="form-input"
                    placeholder="e.g. Micro Labs, Cipla" value={formData.manufacturer} onChange={handleChange} />
                </div>
              </div>

              <div className="grid-2" style={{ gap: '0.75rem' }}>
                <div className="form-group">
                  <label className="form-label" htmlFor="manual-batch">Batch Number</label>
                  <input id="manual-batch" name="batch_number" type="text" className="form-input"
                    placeholder="e.g. ML24A102" value={formData.batch_number} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="manual-expiry">Expiry Date</label>
                  <input id="manual-expiry" name="expiry_date" type="text" className="form-input"
                    placeholder="MM/YYYY or YYYY-MM" value={formData.expiry_date} onChange={handleChange} />
                </div>
              </div>

              <div className="grid-2" style={{ gap: '0.75rem' }}>
                <div className="form-group">
                  <label className="form-label" htmlFor="manual-mrp">MRP (₹)</label>
                  <input id="manual-mrp" name="mrp" type="number" step="0.01" className="form-input"
                    placeholder="e.g. 34.50" value={formData.mrp} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="manual-barcode">
                    Barcode / GTIN <span style={{ color: 'var(--color-primary)', fontSize: '0.75rem' }}>(Fastest)</span>
                  </label>
                  <input id="manual-barcode" name="barcode" type="text" className="form-input"
                    placeholder="13-digit EAN or 14-digit GTIN" value={formData.barcode} onChange={handleChange} />
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <Button variant="secondary" type="button" onClick={onClose}>Cancel</Button>
              <Button type="submit" variant="primary" icon={Search} loading={loading}>
                Screen Against Master DB
              </Button>
            </div>
          </form>
        )}

        {/* Phase: Searching */}
        {phase === 'searching' && (
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '2.5rem' }}>
            <Loader2 size={44} style={{ color: 'var(--color-primary)', animation: 'spin 1s linear infinite' }} />
            <p style={{ fontWeight: 600, fontSize: '1.0625rem' }}>Screening against master database…</p>
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>Checking catalogue records and regulatory alerts</p>
            <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* Phase: Result */}
        {phase === 'result' && searchResult && resultConfig && (
          <>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Result Banner */}
              <div style={{
                backgroundColor: resultConfig.bg,
                border: `1.5px solid ${resultConfig.border}`,
                borderRadius: 'var(--radius-lg)',
                padding: '1.25rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', marginBottom: '0.5rem' }}>
                  <resultConfig.icon size={26} style={{ color: resultConfig.color, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1.0625rem', color: resultConfig.color }}>
                      {resultConfig.label}
                    </div>
                    <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                      Confidence: {Math.round(searchResult.confidence * 100)}%
                    </div>
                  </div>
                </div>
                {searchResult.risk_assessment?.explanation && (
                  <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-main)', lineHeight: 1.5, marginTop: '0.5rem' }}>
                    {searchResult.risk_assessment.explanation}
                  </p>
                )}
              </div>

              {/* Match Details */}
              {searchResult.medicine && (
                <div className="card" style={{ backgroundColor: 'var(--color-bg-subtle)', padding: '1rem' }}>
                  <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
                    Catalogue Match
                  </h4>
                  <div className="grid-2" style={{ gap: '0.625rem', fontSize: '0.875rem' }}>
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', fontSize: '0.75rem', display: 'block' }}>Brand Name</span>
                      <strong>{searchResult.medicine.brand_name}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', fontSize: '0.75rem', display: 'block' }}>Generic Name</span>
                      <strong>{searchResult.medicine.generic_name || 'N/A'}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', fontSize: '0.75rem', display: 'block' }}>Strength</span>
                      <strong>{searchResult.medicine.strength || 'Not specified'}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', fontSize: '0.75rem', display: 'block' }}>Manufacturer</span>
                      <strong>{searchResult.medicine.manufacturer || 'Not available'}</strong>
                    </div>
                    {searchResult.medicine.mrp && (
                      <div>
                        <span style={{ color: 'var(--color-text-subtle)', fontSize: '0.75rem', display: 'block' }}>Catalogue MRP</span>
                        <strong style={{ color: 'var(--color-primary-dark)' }}>₹{Number(searchResult.medicine.mrp).toFixed(2)}</strong>
                      </div>
                    )}
                    {searchResult.medicine.dosage_form && (
                      <div>
                        <span style={{ color: 'var(--color-text-subtle)', fontSize: '0.75rem', display: 'block' }}>Dosage Form</span>
                        <strong>{searchResult.medicine.dosage_form}</strong>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Disclaimer */}
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-disabled)', lineHeight: 1.4, padding: '0 0.25rem' }}>
                MedSure compares details with its catalogue and does not confirm that a medicine is genuine or safe. Consult a pharmacist.
              </p>

              {/* Regulatory Alerts — prominent display when present */}
              {searchResult.regulatory_alerts && searchResult.regulatory_alerts.length > 0 && (
                <div style={{
                  backgroundColor: '#fef2f2',
                  border: '2px solid #ef4444',
                  borderRadius: '8px',
                  padding: '0.875rem',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#dc2626', fontWeight: 700, marginBottom: '0.5rem', fontSize: '0.9375rem' }}>
                    <XCircle size={18} />
                    <span>Active Regulatory Alert(s)</span>
                  </div>
                  {searchResult.regulatory_alerts.map((al, idx) => (
                    <div key={idx} style={{ fontSize: '0.8125rem', color: '#1e293b', marginTop: '0.375rem', paddingLeft: '0.25rem' }}>
                      <strong>{al.alert_type?.replace(/_/g, ' ').toUpperCase()}</strong>
                      {al.batch_number && <> — Batch: <code>{al.batch_number}</code></>}
                      {al.severity && <> · <span style={{ color: al.severity === 'critical' ? '#dc2626' : '#b45309', fontWeight: 600 }}>{al.severity.toUpperCase()}</span></>}
                      {al.description && <div style={{ color: '#475569', marginTop: '0.2rem' }}>{al.description}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <Button variant="secondary" onClick={handleReset}>Check Another</Button>
              <Button variant="primary" onClick={handleConfirmSubmit}>
                {searchResult.status === 'NO_MATCH' ? 'Continue to Full Scan' : 'View Full Result'}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
