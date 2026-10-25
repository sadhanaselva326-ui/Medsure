import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Camera,
  Upload,
  Search,
  Edit3,
  StopCircle,
  X,
  RotateCcw,
  ZoomIn,
  Loader2,
  Image as ImageIcon,
} from 'lucide-react';
import { Button } from '../common/Button';
import { useTranslation } from '../../i18n/LanguageContext';


// ─── Main Component ───────────────────────────────────────────────────────────
export const ScannerFrame = ({
  scannerState, // 'ready' | 'processing'
  onAnalyze,
  onOpenManual,
  onNavigateSearch,
}) => {
  const { t } = useTranslation();

  // 'idle' | 'camera' | 'preview' | 'uploading' | 'upload-confirm'
  const [mode, setMode] = useState('idle');
  const [capturedImage, setCapturedImage] = useState(null); // data-URL
  const [uploadFile, setUploadFile] = useState(null); // { dataUrl, suggestedName }
  const [uploadFields, setUploadFields] = useState({ brand_name: '', barcode: '' });
  const [cameraError, setCameraError] = useState(null);
  const [streamActive, setStreamActive] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);

  // Cleanup camera on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  // ── Camera ─────────────────────────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    setCameraError(null);
    setCapturedImage(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Camera API not available in this browser context.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setStreamActive(true);
      setMode('camera');
    } catch (err) {
      console.warn('Camera error:', err);
      setCameraError(
        err.name === 'NotAllowedError'
          ? 'Camera permission denied. Please allow camera access in your browser settings, or upload an image instead.'
          : 'Camera not available. Please upload a photo of the medicine pack instead.'
      );
      setMode('idle');
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setStreamActive(false);
  }, []);

  const captureFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.88);

    stopCamera();
    setCapturedImage(dataUrl);
    setMode('preview');

    // Send to verification — OCR text extracted from visual context;
    // in a real deployment this would run on-device OCR or send the image to an OCR endpoint.
    // For now we submit the image as a captured frame and let the backend do what it can.
    onAnalyze({
      imagePreview: dataUrl,
      ocr_text: null, // let backend handle empty text gracefully
      barcode: null,
      extracted_fields: null,
    });
  }, [stopCamera, onAnalyze]);

  // ── Image Upload ────────────────────────────────────────────────────────────
  const triggerUpload = () => {
    stopCamera();
    setMode('idle');
    fileInputRef.current?.click();
  };

  const handleFileChange = useCallback(
    (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      e.target.value = '';

      setMode('uploading');
      setCapturedImage(null);

      const reader = new FileReader();
      reader.onload = (ev) => {
        const dataUrl = ev.target?.result;
        // Derive a suggested brand name from the filename
        const rawName = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]+/g, ' ').trim();
        const suggestedName = rawName.split(' ').slice(0, 3).join(' ');
        setCapturedImage(dataUrl);
        setUploadFile({ dataUrl, suggestedName });
        setUploadFields({ brand_name: suggestedName, barcode: '' });
        setMode('upload-confirm');
      };
      reader.onerror = () => {
        setMode('idle');
        setCameraError('Failed to read the selected file. Please try again.');
      };
      reader.readAsDataURL(file);
    },
    []
  );

  const handleUploadConfirm = () => {
    if (!uploadFile) return;
    setCapturedImage(uploadFile.dataUrl);
    setMode('preview');
    onAnalyze({
      imagePreview: uploadFile.dataUrl,
      ocr_text: uploadFields.brand_name || null,
      barcode: uploadFields.barcode || null,
      extracted_fields: uploadFields.brand_name
        ? { brand_name: uploadFields.brand_name }
        : null,
    });
  };

  const resetToIdle = () => {
    stopCamera();
    setCapturedImage(null);
    setCameraError(null);
    setMode('idle');
  };


  // ── Render ──────────────────────────────────────────────────────────────────
  const isProcessing = scannerState === 'processing';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* ── Scanner Viewport ── */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          minHeight: '320px',
          maxHeight: '440px',
          backgroundColor: '#0b1120',
          borderRadius: 'var(--radius-xl)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff',
          boxShadow: 'var(--shadow-md)',
          border: '2px solid rgba(13, 148, 136, 0.3)',
        }}
      >
        {/* Hidden canvas for frame capture */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* ── Live Camera View ── */}
        {mode === 'camera' && streamActive && (
          <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '320px' }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />

            {/* Targeting frame overlay */}
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '78%',
                maxWidth: '380px',
                height: '190px',
                border: '2px dashed #14b8a6',
                borderRadius: 'var(--radius-lg)',
                boxShadow: '0 0 0 9999px rgba(11, 17, 32, 0.52)',
                pointerEvents: 'none',
              }}
            >
              {/* Corner markers */}
              {[
                { top: -2, left: -2, borderTop: '4px solid #14b8a6', borderLeft: '4px solid #14b8a6', borderRadius: '4px 0 0 0' },
                { top: -2, right: -2, borderTop: '4px solid #14b8a6', borderRight: '4px solid #14b8a6', borderRadius: '0 4px 0 0' },
                { bottom: -2, left: -2, borderBottom: '4px solid #14b8a6', borderLeft: '4px solid #14b8a6', borderRadius: '0 0 0 4px' },
                { bottom: -2, right: -2, borderBottom: '4px solid #14b8a6', borderRight: '4px solid #14b8a6', borderRadius: '0 0 4px 0' },
              ].map((style, i) => (
                <div key={i} style={{ position: 'absolute', width: 24, height: 24, ...style }} />
              ))}

              {/* Scanning laser line */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  height: '2px',
                  background: 'linear-gradient(90deg, transparent 0%, #2dd4bf 30%, #2dd4bf 70%, transparent 100%)',
                  boxShadow: '0 0 10px #2dd4bf, 0 0 20px rgba(45, 212, 191, 0.4)',
                  animation: 'scanLaser 2s ease-in-out infinite alternate',
                }}
              />

              <p
                style={{
                  position: 'absolute',
                  bottom: '-2rem',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  whiteSpace: 'nowrap',
                  fontSize: '0.75rem',
                  color: '#94a3b8',
                  fontWeight: 500,
                }}
              >
                Align medicine pack within frame
              </p>
            </div>

            {/* Camera controls */}
            <div
              style={{
                position: 'absolute',
                bottom: '1.25rem',
                left: 0,
                right: 0,
                display: 'flex',
                justifyContent: 'center',
                gap: '0.875rem',
                zIndex: 10,
              }}
            >
              <button
                type="button"
                onClick={stopCamera}
                aria-label="Stop camera"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  padding: '0.5rem 1rem',
                  backgroundColor: 'rgba(220,38,38,0.85)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  cursor: 'pointer',
                  backdropFilter: 'blur(8px)',
                }}
              >
                <StopCircle size={16} />
                Stop
              </button>

              <button
                type="button"
                onClick={captureFrame}
                disabled={isProcessing}
                aria-label="Capture photo"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  padding: '0.5rem 1.25rem',
                  backgroundColor: 'rgba(13,148,136,0.9)',
                  color: '#fff',
                  border: '2px solid rgba(20,184,166,0.5)',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 700,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  backdropFilter: 'blur(8px)',
                }}
              >
                <Camera size={16} />
                Capture
              </button>
            </div>
          </div>
        )}

        {/* ── Uploading spinner ── */}
        {mode === 'uploading' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '2rem' }}>
            <Loader2 size={40} style={{ color: '#14b8a6', animation: 'spin 1s linear infinite' }} />
            <p style={{ color: '#94a3b8', fontSize: '0.9375rem' }}>Reading image file…</p>
          </div>
        )}

        {/* ── Upload Confirm (enter brand + barcode before screening) ── */}
        {mode === 'upload-confirm' && uploadFile && (
          <div style={{ width: '100%', display: 'flex', height: '100%', minHeight: '320px' }}>
            {/* Left: image thumbnail */}
            <div style={{ flex: '0 0 45%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#000', overflow: 'hidden' }}>
              <img src={uploadFile.dataUrl} alt="Uploaded pack" style={{ maxWidth: '100%', maxHeight: '320px', objectFit: 'contain' }} />
            </div>
            {/* Right: quick entry form */}
            <div style={{ flex: 1, padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '0.875rem', backgroundColor: '#0f172a' }}>
              <p style={{ fontSize: '0.8125rem', color: '#94a3b8', lineHeight: 1.45 }}>
                Enter the medicine name or barcode for an accurate screening result.
              </p>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', display: 'block', marginBottom: '0.25rem' }}>Brand / Medicine Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={uploadFields.brand_name}
                  onChange={(e) => setUploadFields((p) => ({ ...p, brand_name: e.target.value }))}
                  placeholder="e.g. Dolo 650"
                  style={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', borderRadius: '8px', padding: '0.5rem 0.75rem', width: '100%', fontSize: '0.875rem' }}
                  autoFocus
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', display: 'block', marginBottom: '0.25rem' }}>Barcode / GTIN <span style={{ color: '#14b8a6', fontSize: '0.6875rem' }}>(Optional — fastest)</span></label>
                <input
                  type="text"
                  className="form-input"
                  value={uploadFields.barcode}
                  onChange={(e) => setUploadFields((p) => ({ ...p, barcode: e.target.value }))}
                  placeholder="e.g. 8901148201201"
                  style={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#e2e8f0', borderRadius: '8px', padding: '0.5rem 0.75rem', width: '100%', fontSize: '0.875rem' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                <button type="button" onClick={resetToIdle}
                  style={{ flex: 1, padding: '0.5rem', borderRadius: '8px', border: '1px solid #334155', backgroundColor: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: '0.8125rem' }}>
                  Cancel
                </button>
                <button type="button" onClick={handleUploadConfirm}
                  disabled={!uploadFields.brand_name.trim() && !uploadFields.barcode.trim()}
                  style={{ flex: 2, padding: '0.5rem', borderRadius: '8px', border: 'none', backgroundColor: '#0d9488', color: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: '0.875rem', opacity: (!uploadFields.brand_name.trim() && !uploadFields.barcode.trim()) ? 0.5 : 1 }}>
                  Screen This Medicine
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Image Preview ── */}
        {mode === 'preview' && capturedImage && (
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              minHeight: '320px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: '#0b1120',
            }}
          >
            <img
              src={capturedImage}
              alt="Medicine packaging"
              style={{ maxWidth: '100%', maxHeight: '400px', objectFit: 'contain' }}
            />

            {/* Processing overlay */}
            {isProcessing && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundColor: 'rgba(11, 17, 32, 0.75)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.875rem',
                  backdropFilter: 'blur(4px)',
                }}
              >
                <Loader2 size={36} style={{ color: '#14b8a6', animation: 'spin 1s linear infinite' }} />
                <p style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '0.9375rem' }}>
                  Screening against master database…
                </p>
                <p style={{ color: '#64748b', fontSize: '0.8125rem' }}>MedSure master catalogue</p>
              </div>
            )}

            {/* Clear button */}
            {!isProcessing && (
              <button
                type="button"
                onClick={resetToIdle}
                aria-label="Remove image"
                style={{
                  position: 'absolute',
                  top: '0.75rem',
                  right: '0.75rem',
                  background: 'rgba(0,0,0,0.65)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '50%',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                }}
              >
                <X size={16} />
              </button>
            )}
          </div>
        )}

        {/* ── Idle / Ready State ── */}
        {mode === 'idle' && !capturedImage && (
          <div style={{ textAlign: 'center', padding: '2rem 1.5rem', maxWidth: '460px' }}>
            <div
              style={{
                width: '68px',
                height: '68px',
                borderRadius: '50%',
                backgroundColor: 'rgba(13, 148, 136, 0.18)',
                border: '1.5px solid rgba(13, 148, 136, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem',
                color: '#14b8a6',
              }}
            >
              <Camera size={34} />
            </div>

            <h3
              style={{
                fontFamily: 'var(--font-family-brand)',
                fontSize: '1.25rem',
                fontWeight: 700,
                marginBottom: '0.5rem',
              }}
            >
              {isProcessing ? t('scan.processing') : t('scan.ready')}
            </h3>

            <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.55, marginBottom: '0.5rem' }}>
              {t('scan.guidance')}
            </p>

            {/* Camera error */}
            {cameraError && (
              <div
                style={{
                  backgroundColor: 'rgba(220,38,38,0.15)',
                  border: '1px solid rgba(220,38,38,0.35)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.625rem 0.875rem',
                  fontSize: '0.8125rem',
                  color: '#fca5a5',
                  marginTop: '0.75rem',
                  textAlign: 'left',
                }}
              >
                ⚠ {cameraError}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Hidden file input — no capture attr so user can pick from gallery or files */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* ── Primary Action Buttons ── */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
        <Button
          id="btn-scan-medicine"
          variant="primary"
          size="lg"
          icon={Camera}
          style={{ flex: '1 1 220px' }}
          onClick={startCamera}
          loading={isProcessing && mode === 'camera'}
          disabled={isProcessing}
        >
          {t('scan.ctaScan')}
        </Button>

        <Button
          id="btn-upload-image"
          variant="secondary"
          size="lg"
          icon={Upload}
          style={{ flex: '1 1 160px' }}
          onClick={triggerUpload}
          disabled={isProcessing}
        >
          {t('scan.ctaUpload')}
        </Button>

        <Button
          id="btn-search-medicine"
          variant="secondary"
          size="lg"
          icon={Search}
          style={{ flex: '1 1 160px' }}
          onClick={onNavigateSearch}
          disabled={isProcessing}
        >
          {t('scan.ctaSearch')}
        </Button>
      </div>

      {/* ── Manual Entry Link ── */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <button
          type="button"
          id="btn-manual-entry"
          onClick={onOpenManual}
          disabled={isProcessing}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.375rem',
            fontSize: '0.875rem',
            color: 'var(--color-primary-dark)',
            fontWeight: 600,
            padding: '0.5rem 0.75rem',
            borderRadius: 'var(--radius-md)',
            textDecoration: 'underline',
            cursor: 'pointer',
            opacity: isProcessing ? 0.5 : 1,
          }}
        >
          <Edit3 size={16} />
          <span>{t('scan.ctaManual')}</span>
        </button>
      </div>


      <style>{`
        @keyframes scanLaser {
          0%   { top: 0%; }
          100% { top: calc(100% - 2px); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};
