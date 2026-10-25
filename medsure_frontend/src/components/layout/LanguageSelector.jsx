import React from 'react';
import { Globe } from 'lucide-react';
import { useTranslation } from '../../i18n/LanguageContext';

export const LanguageSelector = () => {
  const { lang, setLang } = useTranslation();

  const languages = [
    { code: 'en', label: 'English', native: 'English' },
    { code: 'hi', label: 'हिन्दी', native: 'हिन्दी' },
    { code: 'ta', label: 'தமிழ்', native: 'தமிழ்' },
  ];

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem', position: 'relative' }}>
      <Globe size={16} style={{ color: 'var(--color-text-subtle)' }} />
      <select
        value={lang}
        onChange={(e) => setLang(e.target.value)}
        aria-label="Select language"
        className="form-select"
        style={{
          padding: '0.375rem 0.625rem',
          fontSize: '0.8125rem',
          fontWeight: 600,
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'var(--color-bg-subtle)',
          border: '1px solid var(--color-border)',
          cursor: 'pointer',
          width: 'auto',
        }}
      >
        {languages.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </div>
  );
};
