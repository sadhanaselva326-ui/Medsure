import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ShieldCheck,
  PackageCheck,
  RefreshCw,
  Search,
  ExternalLink,
} from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { Button } from '../common/Button';
import { DisclaimerBanner } from '../common/DisclaimerBanner';
import { useTranslation } from '../../i18n/LanguageContext';

export const VerificationResultView = ({
  result,
  scannedData,
  onVerifyAnother,
  onAddToReceiving,
  onSearchCatalog,
}) => {
  const { t } = useTranslation();

  if (!result) return null;

  const rawStatus = (result.status || result.recommendation || '').toUpperCase();
  const overallRisk = (result.risk_assessment?.overall_risk || '').toLowerCase();

  // Determine state mapping to the 5 allowed labels:
  // "Matches a catalogue record" | "Regulatory alert found" | "Needs verification"
  // "No matching record in the MedSure catalogue" | "Insufficient input"
  const LABEL_MATCH = 'Matches a catalogue record';
  const LABEL_ALERT = 'Regulatory alert found';
  const LABEL_NEEDS = 'Needs verification';
  const LABEL_NO_REC = 'No matching record in the MedSure catalogue';
  const LABEL_INSUF = 'Insufficient input';

  let stateKey = 'needsVerification';
  const statusText = result.status || '';
  if (statusText === LABEL_MATCH || rawStatus === 'VERIFIED' || rawStatus.includes('MATCHES')) {
    stateKey = 'match';
  } else if (statusText === LABEL_ALERT || rawStatus === 'HIGH_RISK' || rawStatus.includes('ALERT')) {
    stateKey = 'alert';
  } else if (statusText === LABEL_NO_REC || rawStatus === 'NO_MATCH' || rawStatus.includes('NO RECORD') || rawStatus.includes('NO MATCH')) {
    stateKey = 'noRecord';
  } else if (statusText === LABEL_INSUF || rawStatus.includes('INSUFFICIENT')) {
    stateKey = 'insufficient';
  } else if (statusText === LABEL_NEEDS || rawStatus.includes('NEEDS') || rawStatus.includes('MISMATCH')) {
    stateKey = 'needsVerification';
  }


  const stateConfig = {
    match: {
      badgeText: t('verification.match.badge'),
      title: t('verification.match.title'),
      desc: t('verification.match.desc'),
      bg: 'var(--color-success-bg)',
      border: 'var(--color-success-border)',
      color: 'var(--color-success)',
      Icon: CheckCircle2,
    },
    alert: {
      badgeText: t('verification.alert.badge'),
      title: t('verification.alert.title'),
      desc: t('verification.alert.desc'),
      bg: 'var(--color-danger-bg)',
      border: 'var(--color-danger-border)',
      color: 'var(--color-danger)',
      Icon: XCircle,
    },
    needsVerification: {
      badgeText: t('verification.needsVerification.badge'),
      title: t('verification.needsVerification.title'),
      desc: t('verification.needsVerification.desc'),
      bg: 'var(--color-warning-bg)',
      border: 'var(--color-warning-border)',
      color: 'var(--color-warning)',
      Icon: AlertTriangle,
    },
    noRecord: {
      badgeText: t('verification.noRecord.badge'),
      title: t('verification.noRecord.title'),
      desc: t('verification.noRecord.desc'),
      bg: 'var(--color-bg-subtle)',
      border: 'var(--color-border)',
      color: 'var(--color-text-subtle)',
      Icon: HelpCircle,
    },
    insufficient: {
      badgeText: t('verification.insufficient.badge'),
      title: t('verification.insufficient.title'),
      desc: t('verification.insufficient.desc'),
      bg: 'var(--color-bg-subtle)',
      border: 'var(--color-border)',
      color: 'var(--color-text-subtle)',
      Icon: HelpCircle,
    },
  }[stateKey] || {
    badgeText: 'Needs verification',
    title: 'Needs verification',
    desc: '',
    bg: 'var(--color-warning-bg)',
    border: 'var(--color-warning-border)',
    color: 'var(--color-warning)',
    Icon: AlertTriangle,
  };

  const matched = result.medicine || {};
  const flags = result.risk_assessment?.flags || [];
  const explanation = result.risk_assessment?.explanation || '';
  // Confidence: show only when provided by backend; never fabricate a fallback value
  const rawConfidence = result.confidence ?? result.matched_medicines?.[0]?.confidence_score ?? null;
  const confidencePercent = rawConfidence !== null ? Math.round(rawConfidence * 100) : null;

  // Verification Checklist Items
  const checklist = [
    {
      label: t('verification.checkName'),
      passed: Boolean(matched.brand_name || scannedData?.brand_name),
      detail: matched.brand_name || scannedData?.brand_name || 'Not detected',
    },
    {
      label: t('verification.checkMfg'),
      passed: Boolean(matched.manufacturer || scannedData?.manufacturer),
      detail: matched.manufacturer || scannedData?.manufacturer || 'Check on label',
    },
    {
      label: t('verification.checkStrength'),
      passed: Boolean(matched.strength || scannedData?.strength),
      detail: matched.strength || scannedData?.strength || 'Not verified',
    },
    {
      label: t('verification.checkPack'),
      passed: Boolean(matched.mrp || scannedData?.mrp),
      detail: matched.mrp ? `₹${Number(matched.mrp).toFixed(2)}` : (scannedData?.mrp ? `₹${scannedData.mrp}` : 'MRP unverified'),
    },
    {
      label: t('verification.checkBatch'),
      passed: Boolean(scannedData?.batch_number),
      isWarning: !scannedData?.batch_number,
      detail: scannedData?.batch_number || 'Batch not provided in scan',
    },
    {
      label: t('verification.checkBarcode'),
      passed: Boolean(scannedData?.barcode || scannedData?.gtin),
      isWarning: !scannedData?.barcode && !scannedData?.gtin,
      detail: scannedData?.barcode || scannedData?.gtin || 'Barcode not captured',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', animation: 'fadeIn 250ms ease' }}>
      {/* Primary Result Banner */}
      <div
        className="card"
        style={{
          backgroundColor: stateConfig.bg,
          border: `1.5px solid ${stateConfig.border}`,
          padding: '1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: stateConfig.color,
                boxShadow: 'var(--shadow-sm)',
                flexShrink: 0,
              }}
            >
              <stateConfig.Icon size={28} />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
                <StatusBadge status={stateKey} text={stateConfig.badgeText} size="md" />
                {confidencePercent !== null && (
                <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-subtle)', fontWeight: 600 }}>
                  Confidence: {confidencePercent}%
                </span>
                )}
              </div>
              <h2 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.375rem', fontWeight: 700, color: 'var(--color-text-main)', lineHeight: 1.2 }}>
                {stateConfig.title}
              </h2>
              <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', maxWidth: '580px' }}>
                {stateConfig.desc}
              </p>
            </div>
          </div>
        </div>

        {explanation && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              backgroundColor: 'rgba(255, 255, 255, 0.7)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid rgba(0, 0, 0, 0.05)',
              fontSize: '0.875rem',
              color: 'var(--color-text-main)',
            }}
          >
            <strong>Assessment:</strong> {explanation}
          </div>
        )}
      </div>

      {/* Product Information Table */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700 }}>
            Medicine Screening Details
          </h3>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              padding: '0.2rem 0.5rem',
              borderRadius: '4px',
              backgroundColor: '#fef3c7',
              color: '#92400e',
              border: '1px solid #fde68a',
            }}
          >
            {matched.verification_status === 'verified' ? 'Verified official' : 'Unverified sample data'}
          </span>
        </div>

        <div className="grid-2" style={{ gap: '1rem' }}>
          <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', display: 'block' }}>Brand & Medicine</span>
            <strong style={{ fontSize: '1.0625rem', color: 'var(--color-text-main)' }}>
              {matched.brand_name || scannedData?.brand_name || 'Unidentified Item'}
            </strong>
            <p style={{ fontSize: '0.8125rem', color: 'var(--color-primary-dark)', fontWeight: 600, marginTop: '2px' }}>
              {matched.generic_name || scannedData?.generic_name || 'Generic formulation pending'}
            </p>
          </div>

          <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', display: 'block' }}>Manufacturer</span>
            <strong style={{ fontSize: '0.9375rem', color: 'var(--color-text-main)' }}>
              {matched.manufacturer || scannedData?.manufacturer || 'Declared on package'}
            </strong>
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '2px' }}>
              Source: {matched.source ? matched.source.replace(/_/g, ' ').toUpperCase() : 'Master Catalogue'}
            </p>
          </div>

          <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', display: 'block' }}>Strength & Dosage Form</span>
            <strong style={{ fontSize: '0.9375rem' }}>
              {matched.strength || scannedData?.strength || 'Standard'} • {matched.dosage_form || scannedData?.dosage_form || 'Form not stated'}
            </strong>
          </div>

          <div style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', display: 'block' }}>Pricing & Batch</span>
            <strong style={{ fontSize: '0.9375rem' }}>
              MRP: {matched.mrp ? `₹${Number(matched.mrp).toFixed(2)}` : (scannedData?.mrp ? `₹${scannedData.mrp}` : 'N/A')}
            </strong>
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '2px' }}>
              Batch: {scannedData?.batch_number || 'N/A'} • Exp: {scannedData?.expiry_date || 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* "What was checked" checklist */}
      <div className="card">
        <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700, marginBottom: '0.875rem' }}>
          {t('verification.whatWasChecked')}
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
          {checklist.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.625rem 0.875rem',
                backgroundColor: item.passed ? 'var(--color-bg-subtle)' : (item.isWarning ? 'var(--color-warning-bg)' : 'var(--color-danger-bg)'),
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                {item.passed ? (
                  <CheckCircle2 size={16} style={{ color: 'var(--color-success)' }} />
                ) : item.isWarning ? (
                  <AlertTriangle size={16} style={{ color: 'var(--color-warning)' }} />
                ) : (
                  <XCircle size={16} style={{ color: 'var(--color-danger)' }} />
                )}
                <span style={{ fontWeight: 600 }}>{item.label}</span>
              </div>
              <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                {item.detail}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Regulatory Alerts section if any */}
      {result.regulatory_alerts && result.regulatory_alerts.length > 0 && (
        <div className="card" style={{ border: '1.5px solid var(--color-danger-border)', backgroundColor: 'var(--color-danger-bg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-danger)', fontWeight: 700, marginBottom: '0.5rem' }}>
            <AlertTriangle size={20} />
            <span>Active Regulatory NSQ Alerts for this Medicine</span>
          </div>
          {result.regulatory_alerts.map((al, idx) => (
            <div key={idx} style={{ fontSize: '0.8125rem', color: 'var(--color-text-main)', marginTop: '0.5rem', padding: '0.5rem', backgroundColor: 'rgba(255, 255, 255, 0.7)', borderRadius: 'var(--radius-sm)' }}>
              <div>• <strong>NSQ alert:</strong> {al.description || al.reason_for_nsq}</div>
              {al.testing_lab && <div style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '2px' }}>Testing Lab: {al.testing_lab}</div>}
              {al.source_file_name && (
                <div style={{ fontSize: '0.75rem', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                  <span>Source: <strong>{al.source_file_name}</strong> (Page {al.page_number}{al.row_number ? `, Row ${al.row_number}` : ''})</span>
                  {al.source_url && (
                    <a href={al.source_url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '2px', color: 'var(--color-primary)', textDecoration: 'underline' }}>
                      Official PDF <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Official Evidence & Source Provenance Links */}
      {result.evidence_links && result.evidence_links.length > 0 && (
        <div className="card" style={{ border: '1px solid var(--color-border)', backgroundColor: 'var(--color-bg-subtle)' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-text-main)', marginBottom: '0.5rem' }}>
            Official Source Provenance Links
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            {result.evidence_links.map((link, idx) => (
              <a
                key={idx}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.8125rem',
                  color: 'var(--color-primary)',
                  textDecoration: 'none',
                  padding: '0.375rem 0.5rem',
                  backgroundColor: 'var(--color-bg-card)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <ExternalLink size={14} />
                <span>{link.title}</span>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <DisclaimerBanner />

      {/* Action Buttons */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', justifyContent: 'flex-end', paddingTop: '0.5rem' }}>
        <Button variant="secondary" icon={RefreshCw} onClick={onVerifyAnother}>
          {t('verification.actions.verifyAnother')}
        </Button>

        {onSearchCatalog && matched.brand_name && (
          <Button variant="subtle" icon={Search} onClick={() => onSearchCatalog(matched.brand_name)}>
            View in Master Catalogue
          </Button>
        )}

        {onAddToReceiving && (
          <Button
            variant="primary"
            icon={PackageCheck}
            onClick={() => onAddToReceiving({
              medicine: matched.brand_name || scannedData?.brand_name || 'Scanned Item',
              generic_name: matched.generic_name || scannedData?.generic_name || '',
              manufacturer: matched.manufacturer || scannedData?.manufacturer || 'Unknown',
              batch: scannedData?.batch_number || 'BATCH-UNSPECIFIED',
              expiry: scannedData?.expiry_date || 'N/A',
              mrp: matched.mrp || scannedData?.mrp || 0,
              status: stateKey,
            })}
          >
            {t('verification.actions.addToReceiving')}
          </Button>
        )}
      </div>
    </div>
  );
};
