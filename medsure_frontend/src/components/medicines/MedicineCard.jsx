import React from 'react';
import { Pill, Building2, Tag, ChevronRight, ShieldCheck } from 'lucide-react';
import { Button } from '../common/Button';
import { useTranslation } from '../../i18n/LanguageContext';

export const MedicineCard = ({ medicine, onSelect }) => {
  const { t } = useTranslation();

  return (
    <article className="card card-hoverable" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header with Brand & Dosage Form */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <div>
          <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--color-text-main)', lineHeight: 1.25 }}>
            {medicine.brand_name}
          </h3>
          <p style={{ fontSize: '0.8125rem', color: 'var(--color-primary-dark)', fontWeight: 600, marginTop: '2px' }}>
            {medicine.generic_name}
          </p>
        </div>

        {medicine.dosage_form && (
          <span
            style={{
              fontSize: '0.6875rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              backgroundColor: 'var(--color-bg-subtle)',
              color: 'var(--color-text-muted)',
              padding: '0.2rem 0.5rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              whiteSpace: 'nowrap',
            }}
          >
            {medicine.dosage_form}
          </span>
        )}
      </div>

      {/* Meta specs */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginBottom: '1rem', flex: 1 }}>
        {medicine.strength && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <Pill size={14} style={{ color: 'var(--color-primary)' }} />
            <span><strong>Strength:</strong> {medicine.strength}</span>
          </div>
        )}

        {medicine.manufacturer && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <Building2 size={14} style={{ color: 'var(--color-text-subtle)' }} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <strong>Mfg:</strong> {medicine.manufacturer}
            </span>
          </div>
        )}

        {(medicine.pack_size || medicine.unit) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <Tag size={14} style={{ color: 'var(--color-text-subtle)' }} />
            <span>
              <strong>Packaging:</strong> {medicine.pack_size || ''} {medicine.unit || 'units'}
            </span>
          </div>
        )}
      </div>

      {/* Price & Action */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)' }}>
        <div>
          {medicine.mrp !== undefined && medicine.mrp !== null ? (
            <div>
              <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-subtle)', display: 'block' }}>MRP</span>
              <span style={{ fontSize: '1.0625rem', fontWeight: 700, color: 'var(--color-text-main)' }}>
                ₹{Number(medicine.mrp).toFixed(2)}
              </span>
            </div>
          ) : (
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>Price on catalog</span>
          )}
        </div>

        <Button
          variant="subtle"
          size="sm"
          onClick={() => onSelect(medicine)}
          aria-label={`View details for ${medicine.brand_name}`}
        >
          <span>{t('search.viewDetails')}</span>
          <ChevronRight size={14} />
        </Button>
      </div>
    </article>
  );
};
