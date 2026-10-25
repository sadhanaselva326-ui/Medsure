import React, { useState } from 'react';
import { ScannerFrame } from '../components/scan/ScannerFrame';
import { ManualEntryModal } from '../components/scan/ManualEntryModal';
import { VerificationResultView } from '../components/verification/VerificationResultView';
import { DisclaimerBanner } from '../components/common/DisclaimerBanner';
import { ErrorState } from '../components/common/ErrorState';
import { verificationApi } from '../api/verification';
import { useTranslation } from '../i18n/LanguageContext';

export const ScanPage = ({
  onAddToReceiving,
  onNavigateSearch,
  onRecordHistory,
}) => {
  const { t } = useTranslation();
  const [scannerState, setScannerState] = useState('ready'); // 'ready' | 'processing' | 'result'
  const [result, setResult] = useState(null);
  const [scannedData, setScannedData] = useState(null);
  const [isManualOpen, setIsManualOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lastPayload, setLastPayload] = useState(null);

  // Called by ScannerFrame for camera capture or sample test packs
  const handleAnalyze = async (payload) => {
    setLastPayload(payload);
    setScannerState('processing');
    setErrorMessage(null);

    try {
      // Always call /api/scan/analyze — handles barcode exact match, name fuzzy match,
      // batch-level regulatory alert detection, and full risk assessment in one shot.
      const res = await verificationApi.analyzeScan({
        ocr_text: payload.ocr_text || null,
        barcode: payload.barcode || null,
        gtin: payload.gtin || null,
        extracted_fields: payload.extracted_fields || null,
      });

      // Map ScanAnalyzeResponse → our result shape used by VerificationResultView
      const firstMed = res.matched_medicines?.[0] || null;
      const recommendation = res.risk_assessment?.recommendation || 'NO_MATCH';
      const confidence = firstMed?.confidence_score ?? 0;

      const result = {
        status: recommendation,
        confidence,
        medicine: firstMed ? {
          medicine_id: firstMed.medicine_id,
          brand_name: firstMed.brand_name,
          generic_name: firstMed.generic_name,
          strength: firstMed.strength,
          dosage_form: firstMed.dosage_form,
          manufacturer: firstMed.manufacturer,
          mrp: firstMed.mrp,
          ceiling_price: firstMed.ceiling_price,
          source: firstMed.source,
          match_flags: firstMed.match_flags,
        } : null,
        risk_assessment: res.risk_assessment,
        regulatory_alerts: res.regulatory_alerts || [],
        evidence_links: res.evidence_links || [],
        per_layer_results: res.per_layer_results,
      };

      setResult(result);
      setScannedData(payload.extracted_fields || {});
      setScannerState('result');

      // Record to history ledger
      if (onRecordHistory) {
        onRecordHistory({
          id: Date.now().toString(),
          timestamp: new Date().toISOString(),
          medicine: result.medicine?.brand_name || payload.extracted_fields?.brand_name || 'Unmatched Pack',
          generic_name: result.medicine?.generic_name || payload.extracted_fields?.generic_name || '',
          manufacturer: result.medicine?.manufacturer || payload.extracted_fields?.manufacturer || 'Unknown',
          batch: payload.extracted_fields?.batch_number || 'N/A',
          expiry: payload.extracted_fields?.expiry_date || 'N/A',
          status: result.status || 'NEEDS_VERIFICATION',
          confidence: result.confidence || 0,
        });
      }
    } catch (err) {
      console.error('Verification error:', err);
      setErrorMessage(err.message || 'Unable to communicate with the MedSure verification backend.');
      setScannerState('ready');
    }
  };

  // Called by ManualEntryModal — uses pre-computed result from modal's backend call
  const handleManualSubmit = (formData) => {
    setIsManualOpen(false);

    // If the modal already did the screening, show its result directly
    if (formData._verifyResult) {
      const res = formData._verifyResult;
      setResult(res);
      setScannedData(formData);
      setScannerState('result');

      if (onRecordHistory) {
        onRecordHistory({
          id: Date.now().toString(),
          timestamp: new Date().toISOString(),
          medicine: res.medicine?.brand_name || formData.brand_name || 'Manual Entry',
          generic_name: res.medicine?.generic_name || formData.generic_name || '',
          manufacturer: res.medicine?.manufacturer || formData.manufacturer || 'Unknown',
          batch: formData.batch_number || 'N/A',
          expiry: formData.expiry_date || 'N/A',
          status: res.status || 'NEEDS_VERIFICATION',
          confidence: res.confidence || 0,
        });
      }
    } else {
      // Fallback: run through handleAnalyze
      handleAnalyze({
        ocr_text: `${formData.brand_name} ${formData.generic_name || ''} ${formData.strength || ''} ${formData.manufacturer || ''}`.trim(),
        barcode: formData.barcode || null,
        extracted_fields: formData,
      });
    }
  };

  const handleReset = () => {
    setResult(null);
    setScannedData(null);
    setScannerState('ready');
    setErrorMessage(null);
  };

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Page Header */}
      <div>
        <h1 style={{ fontFamily: 'var(--font-family-brand)', fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-text-main)', letterSpacing: '-0.02em' }}>
          {t('scan.title')}
        </h1>
        <p style={{ fontSize: '1rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', maxWidth: '640px' }}>
          {t('scan.subtitle')}
        </p>
      </div>

      {/* Error display if any */}
      {errorMessage && (
        <ErrorState
          title="Screening Request Failed"
          description={errorMessage}
          onRetry={lastPayload ? () => handleAnalyze(lastPayload) : handleReset}
        />
      )}

      {/* Active Screening Result or Scanner Frame */}
      {scannerState === 'result' && result ? (
        <VerificationResultView
          result={result}
          scannedData={scannedData}
          onVerifyAnother={handleReset}
          onAddToReceiving={onAddToReceiving}
          onSearchCatalog={(brand) => onNavigateSearch(brand)}
        />
      ) : (
        <>
          <ScannerFrame
            scannerState={scannerState}
            onAnalyze={handleAnalyze}
            onOpenManual={() => setIsManualOpen(true)}
            onNavigateSearch={() => onNavigateSearch()}
          />
          <DisclaimerBanner />
        </>
      )}

      {/* Manual Entry Modal */}
      <ManualEntryModal
        isOpen={isManualOpen}
        onClose={() => setIsManualOpen(false)}
        onSubmit={handleManualSubmit}
        loading={scannerState === 'processing'}
      />
    </div>
  );
};
