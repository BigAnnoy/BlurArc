import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../../../contexts/I18nContext';
import { api } from '../../../services/api';

interface UploadedFileInfo {
  name: string;
  size: number;
  status: string;
  error?: string;
}

interface PhoneImportPanelProps {
  onStartImport: (sourcePath: string, sessionId: string) => void;
  onBack: () => void;
}

export function PhoneImportPanel({ onStartImport, onBack }: PhoneImportPanelProps) {
  const { t } = useI18n();

  // Server state
  const [serverStatus, setServerStatus] = useState<'idle' | 'starting' | 'running' | 'error'>('idle');
  const [connectionInfo, setConnectionInfo] = useState<{
    port: number;
    local_ip: string;
    upload_url: string;
    session_id: string;
    upload_dir: string;
  } | null>(null);
  const [qrUrl, setQrUrl] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Files state
  const [files, setFiles] = useState<UploadedFileInfo[]>([]);
  const [completedFiles, setCompletedFiles] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalBytes, setTotalBytes] = useState(0);

  // Resume dialog
  const [showResume, setShowResume] = useState(false);
  const [resumeSession, setResumeSession] = useState<{
    id: string;
    upload_dir: string;
    file_count: number;
    total_bytes: number;
    created_at: number;
  } | null>(null);

  // Start server on mount
  useEffect(() => {
    startServer();
    return () => {
      api.stopPhoneUpload().catch(() => {});
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startServer = async () => {
    setServerStatus('starting');
    setErrorMessage('');

    try {
      const incompleteRes = await api.getIncompletePhoneSession();
      if (incompleteRes.session) {
        setResumeSession(incompleteRes.session);
        setShowResume(true);
        return;
      }

      await doStartServer();
    } catch (error) {
      setServerStatus('error');
      setErrorMessage(error instanceof Error ? error.message : t('phoneImport.serverError'));
    }
  };

  const doStartServer = async () => {
    setServerStatus('starting');
    try {
      const info = await api.startPhoneUpload();
      setConnectionInfo(info);
      setQrUrl(api.getPhoneUploadQr());
      setServerStatus('running');
    } catch (error) {
      setServerStatus('error');
      setErrorMessage(error instanceof Error ? error.message : t('phoneImport.serverError'));
    }
  };

  // Poll status
  useEffect(() => {
    if (serverStatus !== 'running') return;

    let pollErrorCount = 0;
    const interval = setInterval(async () => {
      try {
        const status = await api.getPhoneUploadStatus();
        pollErrorCount = 0; // Reset on success
        setFiles(status.files || []);
        setCompletedFiles(status.completed_files);
        setTotalFiles(status.total_files);
        setTotalBytes(status.total_bytes_uploaded);
      } catch {
        pollErrorCount++;
        // 连续 5 次轮询失败后提示用户
        if (pollErrorCount >= 5) {
          clearInterval(interval);
          setServerStatus('error');
          setErrorMessage(t('phoneImport.serverError'));
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [serverStatus, t]);

  // Handle resume
  const handleResumeContinue = async () => {
    setShowResume(false);
    try {
      const info = await api.resumePhoneSession(resumeSession!.id);
      setConnectionInfo(info);
      setQrUrl(api.getPhoneUploadQr());
      setServerStatus('running');
    } catch (error) {
      setServerStatus('error');
      setErrorMessage(error instanceof Error ? error.message : t('phoneImport.serverError'));
    }
  };

  const handleResumeDiscard = async () => {
    setShowResume(false);
    try {
      await api.discardPhoneSession(resumeSession!.id);
    } catch {
      // Discard 失败也继续 — 后端可能有残留，但不阻塞新会话
    }
    await doStartServer();
  };

  // Handle stop
  const handleStop = async () => {
    try {
      await api.stopPhoneUpload();
    } catch {}
    setServerStatus('idle');
  };

  // Handle start import
  const handleStartImport = useCallback(() => {
    if (!connectionInfo) return;
    if (completedFiles === 0) return;
    onStartImport(connectionInfo.upload_dir, connectionInfo.session_id);
  }, [connectionInfo, completedFiles, onStartImport]);

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes >= 1024 * 1024 * 1024) return (bytes / (1024 ** 3)).toFixed(1) + ' GB';
    if (bytes >= 1024 * 1024) return (bytes / (1024 ** 2)).toFixed(1) + ' MB';
    if (bytes >= 1024) return (bytes / 1024).toFixed(0) + ' KB';
    return bytes + ' B';
  };

  // ===== Resume dialog =====
  if (showResume && resumeSession) {
    const date = new Date(resumeSession.created_at * 1000).toLocaleString();
    const sizeStr = formatSize(resumeSession.total_bytes);

    return (
      <div className="flex flex-col items-center py-6 space-y-6">
        <div className="text-5xl">⚠️</div>
        <h3 className="text-lg font-semibold">{t('phoneImport.resumeTitle')}</h3>
        <p className="text-sm text-text-secondary text-center">
          {t('phoneImport.resumeDetail', { date, count: resumeSession.file_count, size: sizeStr })}
        </p>
        <div className="flex gap-3 w-full">
          <button
            onClick={handleResumeContinue}
            className="flex-1 px-4 py-2.5 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-colors"
          >
            {t('phoneImport.resumeContinue')}
          </button>
          <button
            onClick={handleResumeDiscard}
            className="flex-1 px-4 py-2.5 bg-card border border-border rounded-md text-sm hover:border-primary transition-colors"
          >
            {t('phoneImport.resumeDiscard')}
          </button>
        </div>
      </div>
    );
  }

  // ===== Starting state =====
  if (serverStatus === 'starting') {
    return (
      <div className="flex flex-col items-center py-10 space-y-4">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-text-secondary">{t('phoneImport.starting')}</p>
      </div>
    );
  }

  // ===== Error state =====
  if (serverStatus === 'error') {
    return (
      <div className="flex flex-col items-center py-8 space-y-4">
        <div className="text-4xl">❌</div>
        <p className="text-sm text-text-secondary text-center">{errorMessage}</p>
        <button
          onClick={doStartServer}
          className="px-6 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-colors"
        >
          {t('common.retry')}
        </button>
        <button
          onClick={onBack}
          className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
        >
          {t('preview.back')}
        </button>
      </div>
    );
  }

  // ===== Running state =====
  return (
    <div className="flex flex-col space-y-5">
      {/* Steps guide */}
      <div className="flex items-center gap-2 text-xs text-text-tertiary">
        <span className="w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center text-xs">1</span>
        <span>{t('phoneImport.ensureWifi')}</span>
      </div>

      {/* QR Code */}
      <div className="flex items-start gap-5 p-4 bg-page rounded-lg border border-border">
        <div className="flex-shrink-0">
          <img
            src={qrUrl}
            alt="QR Code"
            className="w-32 h-32 rounded-md border border-border"
          />
        </div>
        <div className="flex-1 min-w-0 space-y-2">
          <p className="text-sm font-medium">{t('phoneImport.scanQr')}</p>
          <div className="text-xs text-text-secondary break-all font-mono bg-card px-2 py-1 rounded border border-border">
            {connectionInfo?.upload_url || ''}
          </div>
          <p className="text-xs text-text-tertiary">{t('phoneImport.receiving')}</p>
        </div>
      </div>

      {/* Files uploaded */}
      {totalFiles > 0 && (
        <div className="p-4 bg-page rounded-lg border border-border">
          <p className="text-sm font-medium mb-2">
            {t('phoneImport.filesUploaded', { count: completedFiles, size: formatSize(totalBytes) })}
          </p>
          <div className="max-h-48 overflow-y-auto space-y-1.5">
            {files.map((f, i) => (
              <div
                key={i}
                className={`flex items-center justify-between text-xs py-1 px-2 rounded ${
                  f.status === 'done'
                    ? 'text-green-600 dark:text-green-400'
                    : f.status === 'failed'
                    ? 'text-red-500'
                    : 'text-text-tertiary'
                }`}
              >
                <span className="truncate flex-1">
                  {f.status === 'done' ? '✅' : f.status === 'failed' ? '❌' : '⏳'}{' '}
                  {f.name}
                </span>
                <span className="flex-shrink-0 ml-2">{f.size > 0 ? formatSize(f.size) : ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleStop}
          className="flex-1 px-4 py-2.5 bg-card border border-border rounded-md text-sm hover:border-primary transition-colors"
        >
          {t('phoneImport.stopReceiving')}
        </button>
        <button
          onClick={handleStartImport}
          disabled={completedFiles === 0}
          className="flex-1 px-4 py-2.5 bg-primary text-white rounded-md text-sm hover:bg-primary-hover disabled:opacity-50 transition-colors"
        >
          {t('phoneImport.startImport')}
        </button>
      </div>

      {/* Back */}
      <button
        onClick={onBack}
        className="text-sm text-text-tertiary hover:text-text-secondary transition-colors self-start"
      >
        ← {t('preview.back')}
      </button>
    </div>
  );
}
