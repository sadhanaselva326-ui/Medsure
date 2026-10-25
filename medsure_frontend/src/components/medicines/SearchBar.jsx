import React, { useState, useEffect, useRef } from 'react';
import { Search, X } from 'lucide-react';
import { useTranslation } from '../../i18n/LanguageContext';

export const SearchBar = ({ value, onChange, onSearch, placeholder, autoFocus = false }) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState(value || '');
  const isFirstRender = useRef(true);

  // Sync internal state if prop value changes externally
  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  // Debounce input changes by 350ms
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    const timer = setTimeout(() => {
      onChange(query);
    }, 350);
    return () => clearTimeout(timer);
  }, [query, onChange]);

  const handleClear = () => {
    setQuery('');
    onChange('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (onSearch) onSearch(query);
    }
  };

  const quickPills = ['Dolo', 'Paracetamol', 'Crocin', 'Amoxicillin', 'Azithromycin', 'Telmisartan'];

  return (
    <div style={{ width: '100%' }}>
      <div className="search-bar-wrap">
        <Search size={18} className="search-icon-left" />
        <input
          type="search"
          className="search-input-field"
          placeholder={placeholder || t('search.placeholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus={autoFocus}
          aria-label="Search medicine catalogue"
        />
        {query && (
          <button
            type="button"
            className="search-clear-btn"
            onClick={handleClear}
            aria-label="Clear search input"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Suggested Quick Searches */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.625rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-subtle)', whiteSpace: 'nowrap' }}>
          {t('search.examples')}
        </span>
        {quickPills.map((pill) => (
          <button
            key={pill}
            type="button"
            onClick={() => {
              setQuery(pill);
              onChange(pill);
              if (onSearch) onSearch(pill);
            }}
            style={{
              padding: '0.25rem 0.625rem',
              fontSize: '0.75rem',
              fontWeight: 500,
              backgroundColor: query.toLowerCase() === pill.toLowerCase() ? 'var(--color-primary-bg)' : 'var(--color-bg-surface)',
              color: query.toLowerCase() === pill.toLowerCase() ? 'var(--color-primary-dark)' : 'var(--color-text-muted)',
              border: '1px solid',
              borderColor: query.toLowerCase() === pill.toLowerCase() ? 'var(--color-primary-border)' : 'var(--color-border)',
              borderRadius: 'var(--radius-full)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 150ms ease',
            }}
          >
            {pill}
          </button>
        ))}
      </div>
    </div>
  );
};
