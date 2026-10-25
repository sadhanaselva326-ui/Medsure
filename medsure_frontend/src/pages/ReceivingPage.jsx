import React, { useState } from 'react';
import {
  PackageCheck,
  Plus,
  Trash2,
  Download,
  Scan,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';
import { Button } from '../components/common/Button';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import { useTranslation } from '../i18n/LanguageContext';

export const ReceivingPage = ({
  receivingLedger = [],
  onRemoveItem,
  onClearLedger,
  onNavigateScan,
}) => {
  const { t } = useTranslation();

  const handleExportCSV = () => {
    if (receivingLedger.length === 0) return;
    const headers = ['Medicine', 'Generic Name', 'Manufacturer', 'Batch Number', 'Expiry Date', 'Quantity', 'MRP', 'Screening Status', 'Added At'];
    const rows = receivingLedger.map((item) => [
      `"${item.medicine || ''}"`,
      `"${item.generic_name || ''}"`,
      `"${item.manufacturer || ''}"`,
      `"${item.batch || ''}"`,
      `"${item.expiry || ''}"`,
      item.quantity || 1,
      item.mrp || 0,
      `"${item.status || ''}"`,
      `"${item.addedAt || new Date().toISOString()}"`,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `medsure_receiving_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const steps = [
    { num: 1, title: 'Scan Pack' },
    { num: 2, title: 'Identify' },
    { num: 3, title: 'Screen' },
    { num: 4, title: 'Review' },
    { num: 5, title: 'Accept into Ledger' },
  ];

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
            {t('receiving.title')}
          </h1>
          <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            {t('receiving.subtitle')}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Button variant="primary" icon={Scan} onClick={onNavigateScan}>
            Screen New Medicine
          </Button>
          {receivingLedger.length > 0 && (
            <Button variant="secondary" icon={Download} onClick={handleExportCSV}>
              Export CSV
            </Button>
          )}
        </div>
      </div>

      {/* Linear Workflow Step Bar */}
      <div className="card" style={{ padding: '1rem' }}>
        <span style={{ fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-primary-dark)', letterSpacing: '0.05em' }}>
          Receiving Protocol
        </span>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginTop: '0.75rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
          {steps.map((step, idx) => (
            <React.Fragment key={step.num}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 'fit-content' }}>
                <div
                  style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--color-primary)',
                    color: '#ffffff',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {step.num}
                </div>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-main)' }}>
                  {step.title}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <ArrowRight size={16} style={{ color: 'var(--color-text-disabled)', flexShrink: 0 }} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Ledger Table */}
      {receivingLedger.length === 0 ? (
        <EmptyState
          icon={PackageCheck}
          title={t('receiving.empty')}
          description="Every incoming medicine shipment should be screened through the scanner or manual entry before acceptance."
          actionLabel="Scan Medicine Now"
          onAction={onNavigateScan}
        />
      ) : (
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
          <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700 }}>
              Verified Inbound Ledger ({receivingLedger.length} items)
            </h3>
            {onClearLedger && (
              <button
                onClick={onClearLedger}
                style={{ fontSize: '0.8125rem', color: 'var(--color-danger)', fontWeight: 600, cursor: 'pointer' }}
              >
                Clear Ledger
              </button>
            )}
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--color-bg-subtle)', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>{t('receiving.tableHeader.medicine')}</th>
                  <th style={{ padding: '0.75rem 1rem' }}>{t('receiving.tableHeader.mfg')}</th>
                  <th style={{ padding: '0.75rem 1rem' }}>{t('receiving.tableHeader.batch')}</th>
                  <th style={{ padding: '0.75rem 1rem' }}>{t('receiving.tableHeader.qty')}</th>
                  <th style={{ padding: '0.75rem 1rem' }}>MRP</th>
                  <th style={{ padding: '0.75rem 1rem' }}>{t('receiving.tableHeader.status')}</th>
                  <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>{t('receiving.tableHeader.action')}</th>
                </tr>
              </thead>
              <tbody>
                {receivingLedger.map((item, index) => (
                  <tr key={index} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '0.875rem 1rem' }}>
                      <strong style={{ display: 'block', color: 'var(--color-text-main)' }}>{item.medicine}</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>{item.generic_name}</span>
                    </td>
                    <td style={{ padding: '0.875rem 1rem', color: 'var(--color-text-muted)' }}>
                      {item.manufacturer}
                    </td>
                    <td style={{ padding: '0.875rem 1rem' }}>
                      <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{item.batch}</span>
                      <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>Exp: {item.expiry}</span>
                    </td>
                    <td style={{ padding: '0.875rem 1rem', fontWeight: 600 }}>
                      {item.quantity || 1} units
                    </td>
                    <td style={{ padding: '0.875rem 1rem', fontWeight: 600 }}>
                      {item.mrp ? `₹${Number(item.mrp).toFixed(2)}` : '—'}
                    </td>
                    <td style={{ padding: '0.875rem 1rem' }}>
                      <StatusBadge status={item.status} size="sm" />
                    </td>
                    <td style={{ padding: '0.875rem 1rem', textAlign: 'right' }}>
                      {onRemoveItem && (
                        <button
                          onClick={() => onRemoveItem(index)}
                          aria-label="Remove item"
                          style={{ color: 'var(--color-text-disabled)', padding: '0.25rem', borderRadius: '4px' }}
                          title="Remove item"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
