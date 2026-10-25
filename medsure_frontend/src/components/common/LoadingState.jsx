import React from 'react';

export const LoadingState = ({ message = 'Loading...', subtitle = 'Please wait while we communicate with the MedSure servers' }) => {
  return (
    <div className="state-container">
      <div className="state-icon-circle" style={{ backgroundColor: 'var(--color-primary-bg)' }}>
        <div className="spinner" />
      </div>
      <h3 className="state-title">{message}</h3>
      {subtitle && <p className="state-description">{subtitle}</p>}
    </div>
  );
};
