import React, { useState } from 'react';
import { History, Search, Filter, Trash2, Calendar, Pill } from 'lucide-react';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';
import { Button } from '../components/common/Button';
import { useTranslation } from '../i18n/LanguageContext';

export const HistoryPage = ({ historyItems = [], onClearHistory, onNavigateScan }) => {
  const { t } = useTranslation();
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filterOptions = [
    { id: 'ALL', label: t('history.filters.all') },
    { id: 'MATCH', label: t('history.filters.match') },
    { id: 'ALERT', label: t('history.filters.alert') },
    { id: 'NEEDS_VERIFICATION', label: t('history.filters.needsVerification') },
  ];

  const filteredItems = historyItems.filter((item) => {
    // Status filter
    if (filterStatus !== 'ALL') {
      const s = (item.status || '').toUpperCase();
      if (filterStatus === 'MATCH' && !s.includes('MATCH') && s !== 'VERIFIED') return false;
      if (filterStatus === 'ALERT' && !s.includes('ALERT') && !s.includes('HIGH_RISK') && !s.includes('MISMATCH')) return false;
      if (filterStatus === 'NEEDS_VERIFICATION' && !s.includes('NEEDS')) return false;
    }

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const medName = (item.medicine || '').toLowerCase();
      const mfg = (item.manufacturer || '').toLowerCase();
      const batch = (item.batch || '').toLowerCase();
      return medName.includes(q) || mfg.includes(q) || batch.includes(q);
    }

    return true;
  });

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
            {t('history.title')}
          </h1>
          <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            {t('history.subtitle')}
          </p>
        </div>

        {historyItems.length > 0 && onClearHistory && (
          <Button variant="secondary" size="sm" icon={Trash2} onClick={onClearHistory}>
            Clear History
          </Button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div className="search-bar-wrap">
          <Search size={18} className="search-icon-left" />
          <input
            type="search"
            className="search-input-field"
            placeholder={t('history.search')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search verification history"
          />
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
          {filterOptions.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setFilterStatus(opt.id)}
              style={{
                padding: '0.375rem 0.875rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                borderRadius: 'var(--radius-full)',
                border: '1px solid',
                borderColor: filterStatus === opt.id ? 'var(--color-primary)' : 'var(--color-border)',
                backgroundColor: filterStatus === opt.id ? 'var(--color-primary-bg)' : 'var(--color-bg-surface)',
                color: filterStatus === opt.id ? 'var(--color-primary-dark)' : 'var(--color-text-muted)',
                whiteSpace: 'nowrap',
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Items list */}
      {filteredItems.length === 0 ? (
        <EmptyState
          icon={History}
          title={t('history.empty')}
          description={
            historyItems.length === 0
              ? 'Start scanning or verifying medicines to see your audit log here.'
              : 'No verification records match your current filter criteria.'
          }
          actionLabel={historyItems.length === 0 ? 'Scan a Medicine' : undefined}
          onAction={historyItems.length === 0 ? onNavigateScan : undefined}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {filteredItems.map((item) => (
            <article
              key={item.id}
              className="card card-hoverable"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem 1.25rem',
                flexWrap: 'wrap',
                gap: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--color-primary-bg)',
                    color: 'var(--color-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Pill size={20} />
                </div>

                <div>
                  <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.0625rem', fontWeight: 700, color: 'var(--color-text-main)' }}>
                    {item.medicine}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '2px', flexWrap: 'wrap' }}>
                    <span>Mfg: <strong>{item.manufacturer}</strong></span>
                    <span>•</span>
                    <span>Batch: <strong style={{ fontFamily: 'monospace' }}>{item.batch}</strong></span>
                    {item.expiry && <span>• Exp: {item.expiry}</span>}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <StatusBadge status={item.status} size="md" />
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
                    <Calendar size={12} />
                    {new Date(item.timestamp).toLocaleString()}
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};
