import React from 'react';
import { PackageOpen } from 'lucide-react';
import { Button } from './Button';

export const EmptyState = ({
  icon: Icon = PackageOpen,
  title = 'No items found',
  description = 'There are no records matching your current selection.',
  actionLabel,
  onAction,
}) => {
  return (
    <div className="state-container">
      <div className="state-icon-circle" style={{ backgroundColor: 'var(--color-bg-subtle)', color: 'var(--color-text-subtle)' }}>
        <Icon size={28} />
      </div>
      <h3 className="state-title">{title}</h3>
      <p className="state-description">{description}</p>
      {actionLabel && onAction && (
        <Button variant="subtle" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
