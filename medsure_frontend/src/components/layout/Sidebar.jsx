import React from 'react';
import {
  Scan,
  PackageCheck,
  History,
  AlertTriangle,
  Search,
  Database,
  ShieldCheck,
  ExternalLink,
} from 'lucide-react';
import { useTranslation } from '../../i18n/LanguageContext';

export const Sidebar = ({ currentTab, onNavigate, alertCount = 0 }) => {
  const { t } = useTranslation();

  const navItems = [
    { id: 'scan', label: t('nav.scan'), icon: Scan },
    { id: 'search', label: t('nav.search'), icon: Search },
    { id: 'receiving', label: t('nav.receiving'), icon: PackageCheck },
    { id: 'history', label: t('nav.history'), icon: History },
    { id: 'alerts', label: t('nav.alerts'), icon: AlertTriangle, count: alertCount },
    { id: 'stats', label: t('nav.stats'), icon: Database },
  ];

  return (
    <aside className="app-sidebar" aria-label="Main Navigation">
      <div className="sidebar-header" onClick={() => onNavigate('scan')} style={{ cursor: 'pointer' }}>
        <img src="/shield-check.svg" alt="MedSure Logo" className="sidebar-logo-icon" />
        <div className="sidebar-brand-text">
          <span className="sidebar-brand-name">MEDSURE</span>
          <span className="sidebar-brand-sub">VISION SCREENING</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon size={18} />
              <span style={{ flex: 1, textAlign: 'left' }}>{item.label}</span>
              {item.count > 0 && (
                <span
                  style={{
                    backgroundColor: 'var(--color-danger)',
                    color: '#fff',
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    padding: '0.125rem 0.4375rem',
                    borderRadius: 'var(--radius-full)',
                  }}
                >
                  {item.count}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div
          style={{
            background: 'var(--color-primary-bg)',
            border: '1px solid var(--color-primary-border)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <ShieldCheck size={16} style={{ color: 'var(--color-primary)' }} />
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary-dark)' }}>
              Catalogue Status
            </span>
          </div>
          <p style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
            Unverified sample data • Official import pending
          </p>
        </div>

        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.75rem',
            color: 'var(--color-text-subtle)',
            padding: '0.375rem 0.5rem',
            borderRadius: 'var(--radius-sm)',
          }}
          className="sidebar-api-link"
        >
          <span>FastAPI Backend Docs</span>
          <ExternalLink size={12} />
        </a>
      </div>
    </aside>
  );
};
