import React from 'react';
import { CheckCircle2, AlertTriangle, HelpCircle, XCircle, Info } from 'lucide-react';

/**
 * Standardized status badge matching MedSure Vision 4 screening states:
 * 1. VERIFIED_MATCH  (catalogue record found, fields match)
 * 2. POTENTIAL MISMATCH
 * 3. NEEDS VERIFICATION
 * 4. NO MATCHING RECORD
 */
export const StatusBadge = ({ status, text, size = 'md' }) => {
  const norm = (status || '').toUpperCase();

  let badgeClass = 'badge-norecord';
  let Icon = HelpCircle;
  let label = text || status;

  if (norm.includes('VERIFIED_MATCH') || norm === 'VERIFIED' || norm === 'LOW') {
    badgeClass = 'badge-verified';
    Icon = CheckCircle2;
    if (!text) label = 'Matches a catalogue record';
  } else if (norm.includes('MISMATCH') || norm.includes('HIGH_RISK') || norm === 'HIGH' || norm === 'CRITICAL') {
    badgeClass = 'badge-mismatch';
    Icon = XCircle;
    if (!text) label = 'Potential Mismatch';
  } else if (norm.includes('NEEDS') || norm.includes('VERIFICATION') || norm === 'MEDIUM') {
    badgeClass = 'badge-verification';
    Icon = AlertTriangle;
    if (!text) label = 'Needs Verification';
  } else if (norm.includes('NO_MATCH') || norm.includes('NO RECORD') || norm.includes('UNKNOWN')) {
    badgeClass = 'badge-norecord';
    Icon = HelpCircle;
    if (!text) label = 'No Record';
  } else if (norm.includes('INFO') || norm.includes('OTC')) {
    badgeClass = 'badge-info';
    Icon = Info;
  }

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  return (
    <span className={`badge ${badgeClass}`} style={{ fontSize: size === 'sm' ? '0.6875rem' : '0.75rem' }}>
      <Icon size={iconSizes[size] || 14} />
      <span>{label}</span>
    </span>
  );
};
