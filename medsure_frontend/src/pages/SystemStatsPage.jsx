import React, { useState, useEffect } from 'react';
import {
  Database,
  Pill,
  Building2,
  Barcode,
  AlertTriangle,
  Activity,
  Layers,
  CheckCircle2,
  Clock,
  ShieldCheck,
  RefreshCw,
  Info,
  XCircle,
} from 'lucide-react';
import { adminApi } from '../api/admin';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { Button } from '../components/common/Button';
import { StatusBadge } from '../components/common/StatusBadge';

const formatSourceName = (name) => {
  if (!name) return 'Unknown';
  const cleanName = name.replace(/\s*\(alerts\)/i, '');
  const map = {
    nppa_ipdms: 'NPPA IPDMS',
    pmbi_janaushadhi: 'PMBI Jan Aushadhi',
    cdsco_nsq: 'CDSCO NSQ',
    abdm_cdci: 'ABDM CDCI',
    gs1_india: 'GS1 India',
    kaggle_dataset: 'Kaggle Dataset',
  };
  return map[cleanName] || cleanName.replace(/_/g, ' ').toUpperCase();
};

export const SystemStatsPage = ({ sessionStats = {} }) => {
  const [dbStats, setDbStats] = useState(null);
  const [dataSources, setDataSources] = useState([]);
  const [healthStatus, setHealthStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, healthRes, sourcesRes] = await Promise.allSettled([
        adminApi.getSystemStats(),
        adminApi.getHealth(),
        adminApi.getDataSources(),
      ]);

      if (statsRes.status === 'fulfilled') {
        setDbStats(statsRes.value);
      } else {
        throw new Error('Could not fetch backend system metrics.');
      }

      if (healthRes.status === 'fulfilled') {
        setHealthStatus(healthRes.value);
      }

      if (sourcesRes.status === 'fulfilled') {
        setDataSources(sourcesRes.value || []);
      }
    } catch (err) {
      console.error('Stats error:', err);
      setError(err.message || 'Failed to retrieve database metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
            System Status & Master Database
          </h1>
          <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Live {healthStatus?.database_engine ? healthStatus.database_engine.toUpperCase() : 'catalogue'} master database metrics and session screening counters.
          </p>
        </div>

        <Button variant="secondary" size="sm" icon={RefreshCw} onClick={fetchStats} loading={loading}>
          Refresh Metrics
        </Button>
      </div>

      {loading ? (
        <LoadingState message="Fetching system status..." subtitle="Querying master catalogue database counters" />
      ) : error ? (
        <ErrorState
          title="Could not load system statistics"
          description={error}
          onRetry={fetchStats}
        />
      ) : (
        <>
          {/* Health & Engine Banner */}
          <div
            className="card"
            style={{
              backgroundColor: 'var(--color-primary-bg)',
              border: '1.5px solid var(--color-primary-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '1.25rem 1.5rem',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-primary)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Activity size={22} />
              </div>
              <div>
                <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--color-primary-darker)' }}>
                  Backend {healthStatus?.database_engine ? healthStatus.database_engine.toUpperCase() : 'Database'} Service: Operational
                </h3>
                <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                  FastAPI service running with {healthStatus?.database_engine ? healthStatus.database_engine.toUpperCase() : 'SQL'} engine (status: {healthStatus?.database || 'ok'})
                </p>
              </div>
            </div>

            <StatusBadge status="low" text="DATABASE CONNECTED" size="md" />
          </div>

          {/* Master Database Metrics Grid */}
          {/* Master Database Metrics Grid */}
          <div>
            {/* Honest Notice Banner */}
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.875rem 1.25rem',
                backgroundColor: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: 'var(--radius-md, 8px)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
              }}
            >
              <AlertTriangle size={20} style={{ color: '#d97706', flexShrink: 0 }} />
              <div style={{ fontSize: '0.875rem', color: '#92400e', fontWeight: 600 }}>
                {dbStats?.notice || 'The catalogue currently contains unverified sample data. Official document import is in progress.'}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.875rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700 }}>
                Master Catalogue Metrics
              </h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    padding: '0.2rem 0.6rem',
                    borderRadius: '9999px',
                    backgroundColor: '#fef3c7',
                    color: '#92400e',
                    border: '1px solid #fde68a',
                  }}
                >
                  Unverified sample data: {dbStats?.unverified_sample ?? dbStats?.total_medicines ?? 119}
                </span>
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    padding: '0.2rem 0.6rem',
                    borderRadius: '9999px',
                    backgroundColor: '#f1f5f9',
                    color: '#475569',
                    border: '1px solid #e2e8f0',
                  }}
                >
                  Verified official: {dbStats?.verified_official ?? 0}
                </span>
              </div>
            </div>

            <div className="grid-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))' }}>
              <div className="card" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)', marginBottom: '0.5rem' }}>
                  <Pill size={20} />
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-subtle)' }}>
                    Sample Medicines
                  </span>
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)', fontFamily: 'var(--font-family-brand)' }}>
                  {(dbStats?.unverified_sample ?? dbStats?.total_medicines ?? 0).toLocaleString()}
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
                  Unverified sample data
                </p>
              </div>

              <div className="card" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)', marginBottom: '0.5rem' }}>
                  <Layers size={20} />
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-subtle)' }}>
                    Total Variants
                  </span>
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)', fontFamily: 'var(--font-family-brand)' }}>
                  {(dbStats?.total_variants || 0).toLocaleString()}
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
                  Specific pack sizes & dosage strengths
                </p>
              </div>

              <div className="card" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)', marginBottom: '0.5rem' }}>
                  <Building2 size={20} />
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-subtle)' }}>
                    Total Manufacturers
                  </span>
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)', fontFamily: 'var(--font-family-brand)' }}>
                  {(dbStats?.total_manufacturers || 0).toLocaleString()}
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
                  Registered pharmaceutical manufacturers
                </p>
              </div>

              <div className="card" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)', marginBottom: '0.5rem' }}>
                  <Barcode size={20} />
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-subtle)' }}>
                    Total Identifiers
                  </span>
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)', fontFamily: 'var(--font-family-brand)' }}>
                  {(dbStats?.total_identifiers || dbStats?.total_codes || 0).toLocaleString()}
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
                  Barcodes, GTINs & drug codes
                </p>
              </div>

              <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #ef4444' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#dc2626', marginBottom: '0.5rem' }}>
                  <AlertTriangle size={20} />
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-subtle)' }}>
                    Regulatory Alerts
                  </span>
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#dc2626', fontFamily: 'var(--font-family-brand)' }}>
                  {(dbStats?.total_alerts || 0).toLocaleString()}
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '0.25rem' }}>
                  Verified: {dbStats?.alerts_verified || 0} • Unverified: {dbStats?.alerts_unverified || 0}
                </p>
              </div>
            </div>
          </div>

          {/* Ingestion Pipeline Audit Section */}
          <div className="card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--color-text-main)' }}>
                  Source Ingestion Pipeline Status
                </h3>
                <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                  Automated ETL pipeline synchronizing official public registries into normalized master records.
                </p>
              </div>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '0.25rem 0.75rem',
                  borderRadius: '9999px',
                  backgroundColor: '#ecfdf5',
                  color: '#065f46',
                  border: '1px solid #a7f3d0',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                }}
              >
                <CheckCircle2 size={14} />
                Idempotent & Deduplicated
              </span>
            </div>

            {/* Last Import Run Card */}
            {dbStats?.last_import_run ? (
              <div
                style={{
                  padding: '1.25rem',
                  borderRadius: 'var(--radius-md, 8px)',
                  backgroundColor: 'var(--color-bg-subtle, #f8fafc)',
                  border: '1px solid var(--color-border, #e2e8f0)',
                  marginBottom: '1.5rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '6px',
                        backgroundColor: '#dbeafe',
                        color: '#1e40af',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Clock size={18} />
                    </div>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                        LAST IMPORT RUN
                      </span>
                      <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-main)' }}>
                        {formatSourceName(dbStats.last_import_run.source_name)} ({dbStats.last_import_run.adapter_name})
                      </h4>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span
                      style={{
                        fontSize: '0.6875rem',
                        fontWeight: 700,
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        backgroundColor:
                          dbStats.last_import_run.status === 'completed' || dbStats.last_import_run.status === 'SUCCESS'
                            ? '#ecfdf5'
                            : '#fee2e2',
                        color:
                          dbStats.last_import_run.status === 'completed' || dbStats.last_import_run.status === 'SUCCESS'
                            ? '#065f46'
                            : '#b91c1c',
                        border: `1px solid ${
                          dbStats.last_import_run.status === 'completed' || dbStats.last_import_run.status === 'SUCCESS'
                            ? '#a7f3d0'
                            : '#fca5a5'
                        }`,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        textTransform: 'uppercase',
                      }}
                    >
                      {dbStats.last_import_run.status === 'completed' || dbStats.last_import_run.status === 'SUCCESS' ? (
                        <>
                          <CheckCircle2 size={12} />
                          COMPLETED
                        </>
                      ) : (
                        <>
                          <XCircle size={12} />
                          FAILED
                        </>
                      )}
                    </span>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
                      {dbStats.last_import_run.completed_at
                        ? new Date(dbStats.last_import_run.completed_at).toLocaleString()
                        : 'Recent'}
                    </span>
                  </div>
                </div>

                {/* Run Outcome Semantic Summary */}
                <div
                  style={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    padding: '0.625rem 0.875rem',
                    marginBottom: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    fontSize: '0.8125rem',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Info size={16} color="var(--color-primary)" />
                    <span>
                      {dbStats.last_import_run.records_imported === 0 && dbStats.last_import_run.records_updated === 0 && dbStats.last_import_run.records_skipped > 0 ? (
                        <>
                          <strong>Process completed:</strong> 0 records actually changed (all{' '}
                          <span style={{ color: '#854d0e', fontWeight: 700 }}>
                            {dbStats.last_import_run.records_skipped} records already existing
                          </span>{' '}
                          in catalogue and skipped).
                        </>
                      ) : dbStats.last_import_run.records_imported > 0 || dbStats.last_import_run.records_updated > 0 ? (
                        <>
                          <strong>Process completed:</strong>{' '}
                          <span style={{ color: '#15803d', fontWeight: 700 }}>
                            {dbStats.last_import_run.records_imported + dbStats.last_import_run.records_updated} records actually changed
                          </span>{' '}
                          ({dbStats.last_import_run.records_imported} imported new, {dbStats.last_import_run.records_updated} updated).
                        </>
                      ) : (
                        <>
                          <strong>Import status:</strong> Import process finished.
                        </>
                      )}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-subtle)' }}>
                    {dbStats.last_import_run.records_read} records processed
                  </span>
                </div>

                {/* Import Run Metrics Counters with semantic labels */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
                  <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', display: 'block' }}>
                      Records Read
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: 'var(--color-text-main)', fontFamily: 'monospace' }}>
                      {dbStats.last_import_run.records_read}
                    </strong>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-subtle)', display: 'block', marginTop: '2px' }}>
                      Read from source
                    </span>
                  </div>

                  <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '6px', border: '1px solid #bbf7d0' }}>
                    <span style={{ fontSize: '0.6875rem', color: '#166534', textTransform: 'uppercase', display: 'block', fontWeight: 600 }}>
                      Records Imported
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: '#15803d', fontFamily: 'monospace' }}>
                      {dbStats.last_import_run.records_imported}
                    </strong>
                    <span style={{ fontSize: '0.6875rem', color: '#166534', display: 'block', marginTop: '2px' }}>
                      Actually changed (new)
                    </span>
                  </div>

                  <div style={{ padding: '0.75rem', backgroundColor: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
                    <span style={{ fontSize: '0.6875rem', color: '#1e40af', textTransform: 'uppercase', display: 'block', fontWeight: 600 }}>
                      Records Updated
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: '#2563eb', fontFamily: 'monospace' }}>
                      {dbStats.last_import_run.records_updated}
                    </strong>
                    <span style={{ fontSize: '0.6875rem', color: '#1e40af', display: 'block', marginTop: '2px' }}>
                      Actually changed (updated)
                    </span>
                  </div>

                  <div style={{ padding: '0.75rem', backgroundColor: '#fefce8', borderRadius: '6px', border: '1px solid #fef08a' }}>
                    <span style={{ fontSize: '0.6875rem', color: '#854d0e', textTransform: 'uppercase', display: 'block', fontWeight: 600 }}>
                      Records Skipped
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: '#a16207', fontFamily: 'monospace' }}>
                      {dbStats.last_import_run.records_skipped}
                    </strong>
                    <span style={{ fontSize: '0.6875rem', color: '#854d0e', display: 'block', marginTop: '2px' }}>
                      Already existing / ignored
                    </span>
                  </div>

                  <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', display: 'block' }}>
                      Errors
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: dbStats.last_import_run.errors_count > 0 ? '#dc2626' : 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                      {dbStats.last_import_run.errors_count}
                    </strong>
                    <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-subtle)', display: 'block', marginTop: '2px' }}>
                      Import failed
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '1.5rem' }}>
                No automated import runs recorded yet. Run `python scripts/data_ingestion/run_ingestion.py` to trigger an ingestion run.
              </p>
            )}

            {/* Recent Import Runs Table */}
            {dbStats?.recent_import_runs && dbStats.recent_import_runs.length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--color-text-main)' }}>
                  Recent Import Runs History
                </h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--color-border, #e2e8f0)', textAlign: 'left', color: 'var(--color-text-muted)' }}>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Source</th>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Adapter</th>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Status</th>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Read</th>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Imported (new)</th>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Updated</th>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Skipped (existing)</th>
                        <th style={{ padding: '0.5rem 0.75rem' }}>Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dbStats.recent_import_runs.map((run, idx) => {
                        const isCompleted = run.status === 'completed' || run.status === 'SUCCESS';
                        const isFailed = run.status === 'failed' || run.status === 'FAILED';
                        return (
                          <tr
                            key={run.run_id || idx}
                            style={{
                              borderBottom: '1px solid var(--color-border, #f1f5f9)',
                              backgroundColor: idx % 2 === 0 ? 'transparent' : 'var(--color-bg-subtle, #f8fafc)',
                            }}
                          >
                            <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600 }}>
                              {formatSourceName(run.source_name)}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                              {run.adapter_name}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem' }}>
                              <span
                                style={{
                                  fontSize: '0.6875rem',
                                  fontWeight: 700,
                                  padding: '0.15rem 0.45rem',
                                  borderRadius: '4px',
                                  backgroundColor: isCompleted ? '#dcfce7' : isFailed ? '#fee2e2' : '#f1f5f9',
                                  color: isCompleted ? '#15803d' : isFailed ? '#b91c1c' : '#475569',
                                  border: `1px solid ${isCompleted ? '#bbf7d0' : isFailed ? '#fecaca' : '#e2e8f0'}`,
                                  textTransform: 'lowercase',
                                }}
                              >
                                {run.status}
                              </span>
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', fontFamily: 'monospace' }}>{run.records_read}</td>
                            <td style={{ padding: '0.625rem 0.75rem', fontFamily: 'monospace', color: '#15803d', fontWeight: 600 }}>
                              {run.records_imported}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', fontFamily: 'monospace', color: '#2563eb' }}>
                              {run.records_updated}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', fontFamily: 'monospace', color: '#a16207' }}>
                              {run.records_skipped}
                            </td>
                            <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-text-muted)' }}>
                              {run.completed_at ? new Date(run.completed_at).toLocaleTimeString() : '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Status semantics legend */}
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '1.25rem',
                    marginTop: '0.75rem',
                    padding: '0.625rem 0.75rem',
                    backgroundColor: 'var(--color-bg-subtle, #f8fafc)',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  <div>
                    <strong style={{ color: '#15803d' }}>completed</strong> = import process completed
                  </div>
                  <div>
                    <strong style={{ color: '#2563eb' }}>imported / updated</strong> = records actually changed
                  </div>
                  <div>
                    <strong style={{ color: '#a16207' }}>skipped</strong> = already existing / ignored records
                  </div>
                  <div>
                    <strong style={{ color: '#b91c1c' }}>failed</strong> = import failed
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Source Provenance & Catalogue Scope Disclaimer */}
          <div className="card" style={{ padding: '1.5rem', backgroundColor: '#fcfdfd', border: '1px solid #e0f2fe' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.75rem' }}>
              <ShieldCheck size={20} color="#0284c7" />
              <h4 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1rem', fontWeight: 700, color: '#0369a1' }}>
                Data Sources & Catalogue Scope Disclaimer
              </h4>
            </div>
            <p style={{ fontSize: '0.8125rem', color: '#334155', lineHeight: 1.5, marginBottom: '0.75rem' }}>
              <strong>Important Scope Notice:</strong> MedSure Vision is an assistive verification aid that ingests
              publicly accessible, downloadable gazette notifications and published catalogues released by Indian regulatory
              authorities (NPPA, PMBI, and CDSCO). <strong>It does NOT claim to contain every medicine marketed in India.</strong>{' '}
              Missing records indicate that a medicine has not yet been ingested into the catalogue.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem', fontSize: '0.8125rem' }}>
              <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <strong style={{ color: '#0f172a', display: 'block' }}>NPPA (DPCO 2013)</strong>
                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>
                  Ceiling prices for National List of Essential Medicines (NLEM) scheduled formulations via S.O. gazettes.
                </span>
              </div>
              <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <strong style={{ color: '#0f172a', display: 'block' }}>PMBI / Jan Aushadhi</strong>
                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>
                  Pradhan Mantri Bhartiya Janaushadhi Pariyojana official product catalogue and subsidized MRP schedule.
                </span>
              </div>
              <div style={{ padding: '0.75rem', backgroundColor: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <strong style={{ color: '#0f172a', display: 'block' }}>CDSCO Monthly NSQ Alerts</strong>
                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>
                  Not of Standard Quality (NSQ) and spurious drug alerts published by Central Drugs Standard Control Organisation.
                </span>
              </div>
            </div>
          </div>

          {/* Session Screenings Summary */}
          <div>
            <h3 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700, marginBottom: '0.875rem' }}>
              Your Session Screenings
            </h3>

            <div className="grid-4">
              <div className="card" style={{ padding: '1rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', display: 'block' }}>Screenings Performed</span>
                <strong style={{ fontSize: '1.5rem', fontFamily: 'var(--font-family-brand)' }}>
                  {sessionStats.totalScreenings || 0}
                </strong>
              </div>

              <div className="card" style={{ padding: '1rem', borderLeft: '3px solid var(--color-success)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-success)', display: 'block', fontWeight: 600 }}>Matches a catalogue record</span>
                <strong style={{ fontSize: '1.5rem', fontFamily: 'var(--font-family-brand)', color: 'var(--color-success)' }}>
                  {sessionStats.matched || 0}
                </strong>
              </div>

              <div className="card" style={{ padding: '1rem', borderLeft: '3px solid var(--color-danger)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-danger)', display: 'block', fontWeight: 600 }}>Regulatory Alerts</span>
                <strong style={{ fontSize: '1.5rem', fontFamily: 'var(--font-family-brand)', color: 'var(--color-danger)' }}>
                  {sessionStats.alerts || sessionStats.mismatches || 0}
                </strong>
              </div>

              <div className="card" style={{ padding: '1rem', borderLeft: '3px solid var(--color-warning)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-warning)', display: 'block', fontWeight: 600 }}>Needs verification</span>
                <strong style={{ fontSize: '1.5rem', fontFamily: 'var(--font-family-brand)', color: 'var(--color-warning)' }}>
                  {sessionStats.needsVerification || 0}
                </strong>
              </div>
            </div>
          </div>

          {/* Coverage by Data Source */}
          <div className="card" style={{ padding: '1.5rem' }}>
            <div style={{ marginBottom: '1rem' }}>
              <h4 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--color-text-main)' }}>
                Master Coverage By Data Source
              </h4>
              <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                Actual counts derived from {healthStatus?.database_engine ? healthStatus.database_engine.toUpperCase() : 'database'} tables and automated ETL ingestion logs.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
              {(() => {
                const rawCoverage = dbStats?.coverage_by_source || {};
                const findCount = (key, alertKey) => {
                  if (rawCoverage[key] !== undefined) return rawCoverage[key];
                  if (alertKey && rawCoverage[alertKey] !== undefined) return rawCoverage[alertKey];
                  const match = dataSources.find((s) => s.source_name === key);
                  return match ? match.coverage_count : 0;
                };

                const sourceList = [
                  {
                    key: 'nppa_ipdms',
                    name: 'NPPA IPDMS',
                    agency: 'National Pharmaceutical Pricing Authority',
                    desc: 'DPCO 2013 ceiling price scheduled formulations',
                    count: findCount('nppa_ipdms'),
                    unit: 'records',
                    isImplemented: true,
                  },
                  {
                    key: 'pmbi_janaushadhi',
                    name: 'PMBI Jan Aushadhi',
                    agency: 'Pharmaceuticals & Medical Devices Bureau of India',
                    desc: 'PMBJP generic medicines & subsidized MRP catalogue',
                    count: findCount('pmbi_janaushadhi'),
                    unit: 'records',
                    isImplemented: true,
                  },
                  {
                    key: 'cdsco_nsq',
                    name: 'CDSCO NSQ',
                    agency: 'Central Drugs Standard Control Organisation',
                    desc: 'Monthly Not of Standard Quality (NSQ) alerts & notices',
                    count: findCount('cdsco_nsq', 'cdsco_nsq (alerts)'),
                    unit: 'alerts',
                    isImplemented: true,
                  },
                  {
                    key: 'abdm_cdci',
                    name: 'ABDM CDCI',
                    agency: 'Ayushman Bharat Digital Mission',
                    desc: 'Central Drug Registry API (Ayushman Bharat)',
                    count: findCount('abdm_cdci'),
                    unit: 'records',
                    isImplemented: false,
                    isPlanned: true,
                  },
                  {
                    key: 'gs1_india',
                    name: 'GS1 India',
                    agency: 'GS1 Standards Organisation India',
                    desc: 'DataKart / SmartSearch Healthcare Barcode & GTIN Registry',
                    count: findCount('gs1_india'),
                    unit: 'records',
                    isImplemented: false,
                    isPlanned: true,
                  },
                  {
                    key: 'kaggle_dataset',
                    name: 'Kaggle Dataset',
                    agency: 'Extensive Indian Medicine Reference',
                    desc: 'Secondary Indian allopathy medicines reference dataset',
                    count: findCount('kaggle_dataset'),
                    unit: 'records',
                    isImplemented: false,
                    isPlanned: true,
                  },
                ];

                return sourceList.map((item) => {
                  const hasRecords = item.count > 0;
                  return (
                    <div
                      key={item.key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.75rem 1rem',
                        backgroundColor: 'var(--color-bg-subtle, #f8fafc)',
                        borderRadius: 'var(--radius-sm, 6px)',
                        border: '1px solid var(--color-border, #f1f5f9)',
                        flexWrap: 'wrap',
                        gap: '0.5rem',
                      }}
                    >
                      <div style={{ flex: '1 1 280px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--color-text-main)' }}>
                            {item.name}
                          </span>
                          {hasRecords && !item.isDemo && (
                            <span
                              style={{
                                fontSize: '0.6875rem',
                                fontWeight: 700,
                                padding: '0.15rem 0.45rem',
                                borderRadius: '4px',
                                backgroundColor: '#ecfdf5',
                                color: '#065f46',
                                border: '1px solid #a7f3d0',
                              }}
                            >
                              Imported (Active)
                            </span>
                          )}
                          {hasRecords && item.isDemo && (
                            <span
                              style={{
                                fontSize: '0.6875rem',
                                fontWeight: 700,
                                padding: '0.15rem 0.45rem',
                                borderRadius: '4px',
                                backgroundColor: '#fef3c7',
                                color: '#92400e',
                                border: '1px solid #fde68a',
                              }}
                            >
                              Demo Baseline
                            </span>
                          )}
                          {!hasRecords && (
                            <span
                              style={{
                                fontSize: '0.6875rem',
                                fontWeight: 600,
                                padding: '0.15rem 0.45rem',
                                borderRadius: '4px',
                                backgroundColor: '#f1f5f9',
                                color: '#64748b',
                                border: '1px solid #e2e8f0',
                              }}
                            >
                              Not imported
                            </span>
                          )}
                        </div>
                        <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                          {item.desc}
                        </p>
                      </div>

                      <div style={{ textAlign: 'right', minWidth: '130px' }}>
                        {hasRecords ? (
                          <strong
                            style={{
                              fontFamily: 'monospace',
                              fontSize: '1rem',
                              color: item.isDemo ? '#92400e' : '#15803d',
                            }}
                          >
                            {Number(item.count).toLocaleString()} {item.unit}
                          </strong>
                        ) : (
                          <span
                            style={{
                              fontSize: '0.8125rem',
                              color: 'var(--color-text-subtle, #94a3b8)',
                              fontStyle: 'italic',
                              fontWeight: 600,
                              fontFamily: 'monospace',
                            }}
                          >
                            Not imported
                          </span>
                        )}
                      </div>
                    </div>
                  );
                });
              })()}
            </div>

            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: '0.875rem', lineHeight: 1.4 }}>
              * Counts represent records actively ingested in the database. Unimplemented or external sources are labeled &quot;Not imported&quot; until loaded by the ingestion pipeline.
            </p>
          </div>
        </>
      )}
    </div>
  );
};
