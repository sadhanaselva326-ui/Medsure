import React from 'react';
import { Scan, PackageCheck, History, AlertTriangle, Search } from 'lucide-react';
import { useTranslation } from '../../i18n/LanguageContext';

export const BottomNavigation = ({ currentTab, onNavigate, alertCount = 0 }) => {
  const { t } = useTranslation();

  const tabs = [
    { id: 'scan', label: t('nav.scan'), icon: Scan },
    { id: 'search', label: t('nav.search'), icon: Search },
    { id: 'receiving', label: t('nav.receiving'), icon: PackageCheck },
    { id: 'history', label: t('nav.history'), icon: History },
    { id: 'alerts', label: t('nav.alerts'), icon: AlertTriangle, count: alertCount },
  ];

  return (
    <nav className="app-bottom-nav" aria-label="Mobile Navigation">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = currentTab === tab.id;
        return (
          <button
            key={tab.id}
            className={`bottom-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => onNavigate(tab.id)}
            aria-label={tab.label}
          >
            <div style={{ position: 'relative' }}>
              <Icon size={20} />
              {tab.count > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-6px',
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--color-danger)',
                  }}
                />
              )}
            </div>
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
