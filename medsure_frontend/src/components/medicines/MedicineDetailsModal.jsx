import React, { useState, useEffect } from 'react';
import {
  X,
  Pill,
  Building2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Package,
  Layers,
  ShieldCheck,
  Tag,
  Barcode,
} from 'lucide-react';
import { medicinesApi } from '../../api/medicines';
import { alertsApi } from '../../api/alerts';
import { Button } from '../common/Button';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';
import { useTranslation } from '../../i18n/LanguageContext';

export const MedicineDetailsModal = ({ medicineId, initialData, onClose, onVerifyThis }) => {
  const { t } = useTranslation();
  const [details, setDetails] = useState(initialData || null);
  const [variants, setVariants] = useState([]);
  const [substitutes, setSubstitutes] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState({
    variants: true,
    substitutes: true,
    composition: true,
    alerts: true,
  });

  useEffect(() => {
    let isMounted = true;
    async function fetchFullData() {
      if (!medicineId) return;
      setLoading(true);
      try {
        const [detailRes, variantsRes, substitutesRes, alertsRes] = await Promise.allSettled([
          medicinesApi.getById(medicineId),
          medicinesApi.getVariants(medicineId),
          medicinesApi.getSubstitutes(medicineId),
          alertsApi.getByMedicineId(medicineId),
        ]);

        if (!isMounted) return;

        if (detailRes.status === 'fulfilled' && detailRes.value) {
          setDetails(detailRes.value);
        }
        if (variantsRes.status === 'fulfilled' && Array.isArray(variantsRes.value)) {
          setVariants(variantsRes.value);
        }
        if (substitutesRes.status === 'fulfilled' && Array.isArray(substitutesRes.value)) {
          setSubstitutes(substitutesRes.value);
        }
        if (alertsRes.status === 'fulfilled' && Array.isArray(alertsRes.value)) {
          setAlerts(alertsRes.value);
        }
      } catch (err) {
        console.error('Error fetching medicine details:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchFullData();
    return () => {
      isMounted = false;
    };
  }, [medicineId]);

  const toggleSection = (sec) => {
    setExpandedSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  if (!medicineId) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" style={{ maxWidth: '720px' }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ paddingRight: '1rem' }}>
            <span style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--color-primary-dark)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Master Medicine Record
            </span>
            <h2 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.375rem', fontWeight: 700, color: 'var(--color-text-main)', marginTop: '2px' }}>
              {details?.brand_name || 'Loading Medicine...'}
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-primary)' }}>
              {details?.generic_name}
            </p>
          </div>
          <button onClick={onClose} aria-label="Close details" style={{ padding: '0.5rem', borderRadius: '50%' }}>
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {loading && !details ? (
            <LoadingState message="Fetching master details..." />
          ) : (
            <>
              {/* Active Alerts Banner if any */}
              {alerts.length > 0 && (
                <div style={{ backgroundColor: 'var(--color-danger-bg)', border: '1px solid var(--color-danger-border)', borderRadius: 'var(--radius-md)', padding: '0.875rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-danger)', fontWeight: 700, fontSize: '0.9375rem', marginBottom: '0.375rem' }}>
                    <AlertTriangle size={18} />
                    <span>{alerts.length} Regulatory Alert(s) on Record</span>
                  </div>
                  {alerts.map((al, idx) => (
                    <div key={idx} style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                      • <strong>{al.alert_type}:</strong> {al.description} {al.batch_number ? `(Batch: ${al.batch_number})` : ''}
                    </div>
                  ))}
                </div>
              )}

              {/* Core Overview Specs Grid */}
              <div className="card" style={{ backgroundColor: 'var(--color-bg-subtle)', padding: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <h4 style={{ fontSize: '0.8125rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-subtle)' }}>
                    {t('details.overview')}
                  </h4>
                  {/* Verification status badge */}
                  {details?.is_demo ? (
                    <span style={{ fontSize: '0.6875rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fde68a' }}>
                      Demo Baseline
                    </span>
                  ) : details?.verification_status === 'verified' ? (
                    <span style={{ fontSize: '0.6875rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', backgroundColor: '#ecfdf5', color: '#065f46', border: '1px solid #a7f3d0' }}>
                      Verified official
                    </span>
                  ) : (
                    <span style={{ fontSize: '0.6875rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fde68a' }}>
                      Unverified sample data
                    </span>
                  )}
                </div>
                <div className="grid-2" style={{ gap: '0.75rem', fontSize: '0.875rem' }}>
                  <div>
                    <span style={{ color: 'var(--color-text-subtle)', display: 'block', fontSize: '0.75rem' }}>Strength</span>
                    <strong>{details?.strength || 'Not specified'}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--color-text-subtle)', display: 'block', fontSize: '0.75rem' }}>Dosage Form</span>
                    <strong>{details?.dosage_form || 'Form not stated'}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--color-text-subtle)', display: 'block', fontSize: '0.75rem' }}>Prescription Category</span>
                    <strong style={{ textTransform: 'capitalize' }}>{details?.prescription_status || 'Prescription'}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--color-text-subtle)', display: 'block', fontSize: '0.75rem' }}>Manufacturer</span>
                    <strong>{details?.manufacturer || 'Registered Indian Pharma'}</strong>
                  </div>
                  {details?.source_name && (
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', display: 'block', fontSize: '0.75rem' }}>Data Source</span>
                      <strong>{details.source_name.replace(/_/g, ' ').toUpperCase()}</strong>
                    </div>
                  )}
                  {details?.last_verified_at && (
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', display: 'block', fontSize: '0.75rem' }}>Last Verified</span>
                      <strong>{new Date(details.last_verified_at).toLocaleDateString()}</strong>
                    </div>
                  )}
                </div>
              </div>

              {/* Section 1: Chemical Composition */}
              <div className="card" style={{ padding: '0.875rem 1rem' }}>
                <div
                  onClick={() => toggleSection('composition')}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9375rem' }}>
                    <Pill size={16} style={{ color: 'var(--color-primary)' }} />
                    <span>{t('details.composition')}</span>
                  </div>
                  {expandedSections.composition ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>

                {expandedSections.composition && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)', fontSize: '0.875rem' }}>
                    {details?.composition && typeof details.composition === 'object' ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                        {Object.entries(details.composition).map(([key, val]) => (
                          <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                            <span style={{ color: 'var(--color-text-muted)' }}>{key}:</span>
                            <span style={{ fontWeight: 600 }}>{String(val)}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: 'var(--color-text-muted)' }}>
                        {details?.generic_name || 'Standard pharmacopoeial salt'}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Section 2: Available Variants & Pack Sizes */}
              <div className="card" style={{ padding: '0.875rem 1rem' }}>
                <div
                  onClick={() => toggleSection('variants')}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9375rem' }}>
                    <Package size={16} style={{ color: 'var(--color-primary)' }} />
                    <span>{t('details.variants')} ({variants.length || (details?.variants?.length || 0)})</span>
                  </div>
                  {expandedSections.variants ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>

                {expandedSections.variants && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)' }}>
                    {(variants.length > 0 ? variants : details?.variants || []).length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {(variants.length > 0 ? variants : details?.variants || []).map((v, i) => (
                          <div
                            key={i}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '0.5rem 0.75rem',
                              backgroundColor: 'var(--color-bg-subtle)',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.8125rem',
                            }}
                          >
                            <div>
                              <span style={{ fontWeight: 600 }}>
                                {v.pack_size ? `${v.pack_size} ${v.unit || 'units'}` : (v.packaging_description || 'Standard Pack')}
                              </span>
                              {v.manufacturer_name && (
                                <span style={{ color: 'var(--color-text-subtle)', display: 'block', fontSize: '0.75rem' }}>
                                  {v.manufacturer_name}
                                </span>
                              )}
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <span style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--color-primary-dark)' }}>
                                {v.mrp ? `₹${Number(v.mrp).toFixed(2)}` : 'MRP on label'}
                              </span>
                              {v.batch_number && (
                                <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--color-text-subtle)' }}>
                                  Batch: {v.batch_number}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                        {details?.pack_size ? `${details.pack_size} ${details.unit || 'units'} - ₹${details.mrp || 'N/A'}` : t('details.noVariants')}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Section 3: Therapeutic Substitutes */}
              <div className="card" style={{ padding: '0.875rem 1rem' }}>
                <div
                  onClick={() => toggleSection('substitutes')}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9375rem' }}>
                    <Layers size={16} style={{ color: 'var(--color-primary)' }} />
                    <span>{t('details.substitutes')} ({substitutes.length || (details?.substitutes?.length || 0)})</span>
                  </div>
                  {expandedSections.substitutes ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>

                {expandedSections.substitutes && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)' }}>
                    {(substitutes.length > 0 ? substitutes : details?.substitutes || []).length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {(substitutes.length > 0 ? substitutes : details?.substitutes || []).map((sub, i) => (
                          <div
                            key={i}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '0.5rem 0.75rem',
                              border: '1px solid var(--color-border)',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.8125rem',
                            }}
                          >
                            <div>
                              <strong style={{ color: 'var(--color-text-main)' }}>{sub.brand_name}</strong>
                              <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                {sub.manufacturer} • {sub.strength}
                              </span>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <span style={{ fontWeight: 700, color: 'var(--color-text-main)' }}>
                                {sub.mrp ? `₹${Number(sub.mrp).toFixed(2)}` : 'MRP N/A'}
                              </span>
                              {sub.similarity_score !== undefined && (
                                <span style={{ display: 'block', fontSize: '0.6875rem', color: 'var(--color-success)', fontWeight: 600 }}>
                                  {Math.round(sub.similarity_score * 100)}% match
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                        {t('details.noSubstitutes')}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <Button variant="secondary" onClick={onClose}>
            {t('common.close')}
          </Button>
          {onVerifyThis && details && (
            <Button
              variant="primary"
              onClick={() => {
                onClose();
                onVerifyThis(details);
              }}
            >
              Verify Package of this Medicine
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
