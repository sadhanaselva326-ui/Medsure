import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  Calendar,
  Building2,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { alertsApi } from '../api/alerts';
import { LoadingState } from '../components/common/LoadingState';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { StatusBadge } from '../components/common/StatusBadge';
import { Button } from '../components/common/Button';
import { useTranslation } from '../i18n/LanguageContext';

export const AlertsPage = () => {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 12, total: 0, total_pages: 1 });
  const [severityFilter, setSeverityFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);

  const fetchAlerts = async (page = 1, severity = '') => {
    setLoading(true);
    setError(null);
    try {
      const res = await alertsApi.list({
        page,
        limit: 12,
        severity: severity || undefined,
        is_active: true,
      });

      setAlerts(res.data || []);
      setPagination(res.pagination || { page, limit: 12, total: res.data?.length || 0, total_pages: 1 });
    } catch (err) {
      console.error('Failed to fetch regulatory alerts:', err);
      setError(err.message || 'Unable to connect to regulatory alerts server.');
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts(pagination.page, severityFilter);
  }, [pagination.page, severityFilter]);

  const severityOptions = [
    { value: '', label: 'All Severities' },
    { value: 'critical', label: 'Critical Alerts' },
    { value: 'warning', label: 'Warnings / Advisories' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low / Info' },
  ];

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
            {t('alerts.title')}
          </h1>
          <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            {t('alerts.subtitle')}
          </p>
        </div>

        {/* Severity Filter dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={16} style={{ color: 'var(--color-text-subtle)' }} />
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setPagination((p) => ({ ...p, page: 1 }));
            }}
            className="form-select"
            style={{ width: 'auto', fontSize: '0.8125rem', padding: '0.4rem 0.8rem' }}
            aria-label="Filter alerts by severity"
          >
            {severityOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Content */}
      {loading ? (
        <LoadingState message="Fetching live regulatory alerts..." subtitle="Querying CDSCO and Indian regulatory NSQ alert feed" />
      ) : error ? (
        <ErrorState
          title="Could not load regulatory alerts"
          description={error}
          onRetry={() => fetchAlerts(pagination.page, severityFilter)}
        />
      ) : alerts.length === 0 ? (
        <EmptyState
          icon={AlertTriangle}
          title={t('alerts.empty')}
          description="There are currently no active regulatory alerts matching your filter in the MedSure database."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="grid-2" style={{ gap: '1rem' }}>
            {alerts.map((al) => {
              const isCrit = (al.severity || '').toLowerCase() === 'critical';
              return (
                <article
                  key={al.alert_id}
                  className="card card-hoverable"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    borderLeft: `4px solid ${isCrit ? 'var(--color-danger)' : 'var(--color-warning)'}`,
                    gap: '0.625rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
                    <StatusBadge
                      status={al.severity}
                      text={al.severity?.toUpperCase()}
                      size="sm"
                    />
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>
                      <Calendar size={12} />
                      {al.alert_date || new Date(al.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div>
                    <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.0625rem', fontWeight: 700, color: 'var(--color-text-main)', lineHeight: 1.3 }}>
                      {al.brand_name ? `${al.brand_name}: ${al.alert_type}` : al.alert_type}
                    </h3>
                    {al.manufacturer && (
                      <p style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                        <Building2 size={13} style={{ color: 'var(--color-text-subtle)' }} />
                        <span>{al.manufacturer}</span>
                      </p>
                    )}
                  </div>

                  <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', lineHeight: 1.5, flex: 1 }}>
                    {al.description}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.625rem', borderTop: '1px solid var(--color-border)', fontSize: '0.75rem' }}>
                    {al.batch_number ? (
                      <span style={{ color: 'var(--color-danger)', fontWeight: 600 }}>
                        {t('alerts.affectedBatch')}: <strong style={{ fontFamily: 'monospace' }}>{al.batch_number}</strong>
                      </span>
                    ) : (
                      <span style={{ color: 'var(--color-text-subtle)' }}>All Batches Monitored</span>
                    )}

                    {al.source_url ? (
                      <a
                        href={al.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--color-primary-dark)', fontWeight: 600 }}
                      >
                        <span>Official Notice</span>
                        <ExternalLink size={12} />
                      </a>
                    ) : (
                      <span style={{ color: 'var(--color-text-subtle)' }}>Source: CDSCO / State DC</span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 0' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                Page {pagination.page} of {pagination.total_pages} ({pagination.total} alerts)
              </span>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={ChevronLeft}
                  onClick={() => setPagination((p) => ({ ...p, page: Math.max(1, p.page - 1) }))}
                  disabled={pagination.page <= 1}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setPagination((p) => ({ ...p, page: Math.min(p.total_pages, p.page + 1) }))}
                  disabled={pagination.page >= pagination.total_pages}
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
