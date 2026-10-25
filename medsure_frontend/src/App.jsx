import React, { useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { BottomNavigation } from './components/layout/BottomNavigation';
import { ScanPage } from './pages/ScanPage';
import { SearchPage } from './pages/SearchPage';
import { ReceivingPage } from './pages/ReceivingPage';
import { HistoryPage } from './pages/HistoryPage';
import { AlertsPage } from './pages/AlertsPage';
import { SystemStatsPage } from './pages/SystemStatsPage';
import { alertsApi } from './api/alerts';
import { LanguageProvider } from './i18n/LanguageContext';

export function MedSureApp() {
  const [currentTab, setCurrentTab] = useState('scan');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeAlertsCount, setActiveAlertsCount] = useState(0);

  // Persistent History
  const [historyItems, setHistoryItems] = useState(() => {
    try {
      const saved = localStorage.getItem('medsure_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Persistent Receiving Ledger
  const [receivingLedger, setReceivingLedger] = useState(() => {
    try {
      const saved = localStorage.getItem('medsure_receiving');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('medsure_history', JSON.stringify(historyItems));
    } catch (e) {
      console.error('Failed to save history to storage', e);
    }
  }, [historyItems]);

  useEffect(() => {
    try {
      localStorage.setItem('medsure_receiving', JSON.stringify(receivingLedger));
    } catch (e) {
      console.error('Failed to save receiving ledger to storage', e);
    }
  }, [receivingLedger]);

  // Fetch initial alerts count from backend
  useEffect(() => {
    async function loadAlertsCount() {
      try {
        const res = await alertsApi.list({ page: 1, limit: 1, is_active: true });
        if (res && res.pagination) {
          setActiveAlertsCount(res.pagination.total || 0);
        }
      } catch (err) {
        // Soft fail if server unavailable
        console.warn('Could not fetch alerts count:', err);
      }
    }
    loadAlertsCount();
  }, []);

  // Handlers
  const handleRecordHistory = (item) => {
    setHistoryItems((prev) => [item, ...prev]);
  };

  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear your verification audit log?')) {
      setHistoryItems([]);
    }
  };

  const handleAddToReceiving = (item) => {
    setReceivingLedger((prev) => [
      {
        ...item,
        quantity: 1,
        addedAt: new Date().toISOString(),
      },
      ...prev,
    ]);
    setCurrentTab('receiving');
  };

  const handleRemoveReceivingItem = (index) => {
    setReceivingLedger((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClearReceivingLedger = () => {
    if (window.confirm('Clear all items from the inbound receiving ledger?')) {
      setReceivingLedger([]);
    }
  };

  const handleNavigateSearch = (initialTerm = '') => {
    setSearchQuery(initialTerm);
    setCurrentTab('search');
  };

  // Derive session statistics from actual screening history
  const sessionStats = {
    totalScreenings: historyItems.length,
    verified: historyItems.filter((i) => {
      const s = (i.status || '').toUpperCase();
      return s.includes('VERIFIED_MATCH') || s === 'VERIFIED';
    }).length,
    mismatches: historyItems.filter((i) => {
      const s = (i.status || '').toUpperCase();
      return s.includes('MISMATCH') || s.includes('HIGH_RISK');
    }).length,
    needsVerification: historyItems.filter((i) => {
      const s = (i.status || '').toUpperCase();
      return s.includes('NEEDS');
    }).length,
  };

  return (
    <div className="app-container">
      {/* Desktop Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onNavigate={setCurrentTab}
        alertCount={activeAlertsCount}
      />

      {/* Main Content Area */}
      <div className="app-main">
        <Header
          currentTab={currentTab}
          onNavigate={setCurrentTab}
        />

        <main style={{ flex: 1 }}>
          {currentTab === 'scan' && (
            <ScanPage
              onAddToReceiving={handleAddToReceiving}
              onNavigateSearch={handleNavigateSearch}
              onRecordHistory={handleRecordHistory}
            />
          )}

          {currentTab === 'search' && (
            <SearchPage
              initialQuery={searchQuery}
              onVerifyMedicine={(med) => {
                setCurrentTab('scan');
              }}
            />
          )}

          {currentTab === 'receiving' && (
            <ReceivingPage
              receivingLedger={receivingLedger}
              onRemoveItem={handleRemoveReceivingItem}
              onClearLedger={handleClearReceivingLedger}
              onNavigateScan={() => setCurrentTab('scan')}
            />
          )}

          {currentTab === 'history' && (
            <HistoryPage
              historyItems={historyItems}
              onClearHistory={handleClearHistory}
              onNavigateScan={() => setCurrentTab('scan')}
            />
          )}

          {currentTab === 'alerts' && (
            <AlertsPage />
          )}

          {currentTab === 'stats' && (
            <SystemStatsPage sessionStats={sessionStats} />
          )}
        </main>

        {/* Mobile Bottom Navigation */}
        <BottomNavigation
          currentTab={currentTab}
          onNavigate={setCurrentTab}
          alertCount={activeAlertsCount}
        />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <MedSureApp />
    </LanguageProvider>
  );
}
