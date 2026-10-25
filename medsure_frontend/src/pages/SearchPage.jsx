import React, { useState, useEffect, useCallback } from 'react';
import { SearchBar } from '../components/medicines/SearchBar';
import { MedicineCard } from '../components/medicines/MedicineCard';
import { MedicineDetailsModal } from '../components/medicines/MedicineDetailsModal';
import { LoadingState } from '../components/common/LoadingState';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { Button } from '../components/common/Button';
import { ChevronLeft, ChevronRight, Filter, RefreshCw, Zap } from 'lucide-react';
import { medicinesApi } from '../api/medicines';
import { useTranslation } from '../i18n/LanguageContext';

export const SearchPage = ({ initialQuery = '', onVerifyMedicine }) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState(initialQuery || 'Dolo');
  const [dosageForm, setDosageForm] = useState('');
  const [page, setPage] = useState(1);
  const limit = 18;

  const [medicines, setMedicines] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 18, total: 0, total_pages: 1 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [responseTimeMs, setResponseTimeMs] = useState(null);
  const [selectedMedicine, setSelectedMedicine] = useState(null);

  const fetchSearchResults = useCallback(async (searchQuery, targetPage, targetForm) => {
    if (!searchQuery.trim()) {
      setMedicines([]);
      setPagination({ page: 1, limit, total: 0, total_pages: 0 });
      return;
    }

    setLoading(true);
    setError(null);
    const startTime = performance.now();

    try {
      const res = await medicinesApi.search({
        q: searchQuery,
        page: targetPage,
        limit,
        dosage_form: targetForm || undefined,
      });

      const elapsed = Math.round(performance.now() - startTime);
      setResponseTimeMs(elapsed);

      setMedicines(res.data || []);
      setPagination(res.pagination || { page: targetPage, limit, total: res.data?.length || 0, total_pages: 1 });
    } catch (err) {
      console.error('Search error:', err);
      setError(err.message || 'Failed to search medicines master database.');
      setMedicines([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  // Perform search on query, page, or dosageForm changes
  useEffect(() => {
    fetchSearchResults(query, page, dosageForm);
  }, [query, page, dosageForm, fetchSearchResults]);

  const handleQueryChange = (newQuery) => {
    setQuery(newQuery);
    setPage(1);
  };

  const handleFormChange = (e) => {
    setDosageForm(e.target.value);
    setPage(1);
  };

  const formsList = ['Tablet', 'Capsule', 'Syrup', 'Injection', 'Ointment', 'Drops', 'Suspension'];

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Search Header */}
      <div>
        <h1 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
          {t('search.title')}
        </h1>
        <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
          Full-text search across master catalogue (unverified sample data).
        </p>
      </div>

      {/* Search bar & Filter row */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
        <SearchBar
          value={query}
          onChange={handleQueryChange}
          onSearch={(q) => handleQueryChange(q)}
          autoFocus={!initialQuery}
        />

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={16} style={{ color: 'var(--color-text-subtle)' }} />
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>
              {t('search.filterBy')}:
            </span>
            <select
              value={dosageForm}
              onChange={handleFormChange}
              className="form-select"
              style={{
                width: 'auto',
                padding: '0.375rem 0.75rem',
                fontSize: '0.8125rem',
                borderRadius: 'var(--radius-md)',
              }}
              aria-label="Filter by dosage form"
            >
              <option value="">{t('search.allForms')}</option>
              {formsList.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>

          {/* Response metrics */}
          {responseTimeMs !== null && !loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.75rem', color: 'var(--color-primary-dark)', fontWeight: 600 }}>
              <Zap size={14} style={{ color: 'var(--color-primary)' }} />
              <span>Query resolved in {responseTimeMs}ms</span>
              {pagination.total > 0 && (
                <span style={{ color: 'var(--color-text-subtle)', fontWeight: 400 }}>
                  â¢ {pagination.total.toLocaleString()} matches
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Results Container */}
      <div>
        {loading ? (
          <LoadingState message={t('search.searching')} subtitle="Searching master catalogue" />
        ) : error ? (
          <ErrorState
            title="Search Request Failed"
            description={error}
            onRetry={() => fetchSearchResults(query, page, dosageForm)}
          />
        ) : medicines.length === 0 ? (
          <EmptyState
            title={t('search.noResults')}
            description={`No medicines found for "${query}". Try searching for generic salt like "Paracetamol", brand like "Crocin", or remove filters.`}
            actionLabel="Try searching 'Paracetamol'"
            onAction={() => handleQueryChange('Paracetamol')}
          />
        ) : (
          <>
            {/* Grid of Results */}
            <div className="grid-3" style={{ gap: '1rem', marginBottom: '1.5rem' }}>
              {medicines.map((med) => (
                <MedicineCard
                  key={med.medicine_id}
                  medicine={med}
                  onSelect={(item) => setSelectedMedicine(item)}
                />
              ))}
            </div>

            {/* Pagination Controls */}
            {pagination.total_pages > 1 && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1rem 0',
                  borderTop: '1px solid var(--color-border)',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                }}
              >
                <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                  Page <strong>{pagination.page}</strong> of <strong>{pagination.total_pages}</strong> ({pagination.total.toLocaleString()} total items)
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={ChevronLeft}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={pagination.page <= 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
                    disabled={pagination.page >= pagination.total_pages}
                  >
                    <span>Next</span>
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Full Medicine Details Modal */}
      {selectedMedicine && (
        <MedicineDetailsModal
          medicineId={selectedMedicine.medicine_id}
          initialData={selectedMedicine}
          onClose={() => setSelectedMedicine(null)}
          onVerifyThis={(med) => {
            if (onVerifyMedicine) onVerifyMedicine(med);
          }}
        />
      )}
    </div>
  );
};
