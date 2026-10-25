import React from 'react';
import { ShieldAlert } from 'lucide-react';

export const DisclaimerBanner = ({ style = {} }) => {
  return (
    <aside className="disclaimer-banner" style={style} aria-label="Product positioning disclaimer">
      <ShieldAlert size={18} style={{ color: 'var(--color-primary-dark)', flexShrink: 0, marginTop: '2px' }} />
      <div>
        <strong>Disclaimer:</strong> MedSure compares details with its catalogue and does not confirm that a medicine is genuine or safe. Consult a pharmacist.
      </div>
    </aside>
  );
};
