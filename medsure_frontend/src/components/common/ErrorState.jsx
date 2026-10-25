import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export const ErrorState = ({
  title = 'Something went wrong',
  description = 'Unable to connect to the MedSure server or fetch data. Please try again.',
  onRetry,
  retryLabel = 'Try Again',
}) => {
  return (
    <div className="state-container">
      <div className="state-icon-circle" style={{ backgroundColor: 'var(--color-danger-bg)', color: 'var(--color-danger)' }}>
        <AlertCircle size={28} />
      </div>
      <h3 className="state-title">{title}</h3>
      <p className="state-description" style={{ color: 'var(--color-danger)' }}>
        {description}
      </p>
      {onRetry && (
        <Button variant="secondary" icon={RefreshCw} onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
};
