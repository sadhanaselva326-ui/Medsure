import React, { useState } from 'react';
import { ShieldCheck, HelpCircle, Activity } from 'lucide-react';
import { LanguageSelector } from './LanguageSelector';
import { HelpModal } from './HelpModal';
import { useTranslation } from '../../i18n/LanguageContext';

export const Header = ({ currentTab, onNavigate }) => {
  const { t } = useTranslation();
  const [showHelp, setShowHelp] = useState(false);

  const tabTitles = {
    scan: t('scan.title'),
    search: t('search.title'),
    receiving: t('receiving.title'),
    history: t('history.title'),
    alerts: t('alerts.title'),
    stats: 'System Status & Database',
  };

  return (
    <>
      <header className="app-header">
        <div className="header-left">
          {/* Mobile Logo */}
          <div className="header-logo-mobile" onClick={() => onNavigate('scan')} style={{ cursor: 'pointer' }}>
            <img src="/shield-check.svg" alt="MedSure Logo" style={{ width: '28px', height: '28px' }} />
            <div>
              <span style={{ fontFamily: 'var(--font-family-brand)', fontWeight: 700, fontSize: '1rem', color: 'var(--color-primary-dark)' }}>
                MEDSURE
              </span>
              <span style={{ fontSize: '0.625rem', display: 'block', color: 'var(--color-primary)', fontWeight: 700, letterSpacing: '0.05em' }}>
                VISION
              </span>
            </div>
          </div>

          {/* Desktop Title */}
          <h1 className="header-title-desktop">
            {tabTitles[currentTab] || 'MedSure Vision'}
          </h1>
        </div>

        <div className="header-actions">
          {/* Real-time server indicator */}
          <div
            title="Connected to MedSure Live Backend"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--color-success)',
              background: 'var(--color-success-bg)',
              padding: '0.25rem 0.625rem',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--color-success-border)',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-success)',
                display: 'inline-block',
                boxShadow: '0 0 0 2px rgba(5, 150, 105, 0.2)',
              }}
            />
            <span className="desktop-only" style={{ display: 'inline' }}>Master DB Live</span>
          </div>

          <LanguageSelector />

          <button
            onClick={() => setShowHelp(true)}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.4375rem', borderRadius: 'var(--radius-md)' }}
            title={t('nav.help')}
            aria-label="Open screening guidance"
          >
            <HelpCircle size={18} />
          </button>
        </div>
      </header>

      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
    </>
  );
};
