import React, { useState, useEffect } from 'react';
import { X, ShieldCheck, AlertTriangle, XCircle, HelpCircle, CheckCircle, Info } from 'lucide-react';
import { Button } from '../common/Button';
import { request } from '../../api/client';

export const HelpModal = ({ isOpen, onClose }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (isOpen) {
      request('/api/stats')
        .then((data) => setStats(data))
        .catch(() => setStats(null));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const totalMeds = stats?.total_medicines ? `${stats.total_medicines} sample medicines` : 'catalogue medicines';

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="help-title">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <ShieldCheck size={24} style={{ color: 'var(--color-primary)' }} />
            <h2 id="help-title" style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.25rem' }}>
              MedSure Vision Screening Guide
            </h2>
          </div>
          <button onClick={onClose} aria-label="Close modal" style={{ padding: '0.375rem', borderRadius: '50%' }}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <h4 style={{ fontWeight: 700, marginBottom: '0.375rem', color: 'var(--color-primary-dark)' }}>
              First-Line Screening Principles
            </h4>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
              MedSure Vision cross-references published Indian public health catalogues (including PMBI Jan Aushadhi generic schedules, NPPA DPCO ceiling price notifications, and CDSCO laboratory quality alerts covering {totalMeds}) to screen packaging, dosage forms, declared details, and batches flagged in NSQ notices.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <h4 style={{ fontWeight: 700, fontSize: '0.9375rem' }}>Screening Result Categories:</h4>

            <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'var(--color-success-bg)', border: '1px solid var(--color-success-border)' }}>
              <CheckCircle size={20} style={{ color: 'var(--color-success)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--color-success)', fontSize: '0.875rem' }}>Matches a catalogue record</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>Brand name, generic formulation, strength, and pack details match registered catalogue entries.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'var(--color-warning-bg)', border: '1px solid var(--color-warning-border)' }}>
              <AlertTriangle size={20} style={{ color: 'var(--color-warning)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--color-warning)', fontSize: '0.875rem' }}>Needs verification</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>A field mismatch (such as strength or dosage form) was detected, or partial input requires manual review.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'var(--color-danger-bg)', border: '1px solid var(--color-danger-border)' }}>
              <XCircle size={20} style={{ color: 'var(--color-danger)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--color-danger)', fontSize: '0.875rem' }}>Regulatory alert found</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>The submitted batch number matches a Not of Standard Quality (NSQ) advisory or regulatory alert.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)' }}>
              <HelpCircle size={20} style={{ color: 'var(--color-text-subtle)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--color-text-subtle)', fontSize: '0.875rem' }}>No matching record in the MedSure catalogue</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>Medicine brand or formulation could not be found in the current MedSure catalogue.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem', borderRadius: 'var(--radius-md)', background: '#f8fafc', border: '1px solid var(--color-border)' }}>
              <Info size={20} style={{ color: 'var(--color-text-subtle)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--color-text-subtle)', fontSize: '0.875rem' }}>Insufficient input</div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>No medicine name, barcode, or batch number was provided to perform screening.</div>
              </div>
            </div>
          </div>

          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '0.75rem', borderRadius: 'var(--radius-md)', fontSize: '0.8125rem', color: '#991b1b', lineHeight: 1.4 }}>
            <strong>Important Disclaimer:</strong> MedSure compares details with its catalogue and does not confirm that a medicine is genuine or safe. Consult a pharmacist.
          </div>
        </div>

        <div className="modal-footer">
          <Button variant="primary" onClick={onClose}>
            Got it, thanks
          </Button>
        </div>
      </div>
    </div>
  );
};
