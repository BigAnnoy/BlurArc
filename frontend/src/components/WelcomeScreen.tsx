import { useState, useEffect, useRef, useCallback } from 'react';
import { useI18n } from '../contexts/I18nContext';
import { useToast } from './common/Toast';
import { api } from '../services/api';

interface WelcomeScreenProps {
  onComplete: () => void;
}

const POLL_INTERVAL = 500;
const MAX_RETRY_COUNT = 5;

export function WelcomeScreen({ onComplete }: WelcomeScreenProps) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const pollingRef = useRef<boolean>(false);
  const retryCountRef = useRef<number>(0);
  const onCompleteCalledRef = useRef<boolean>(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const finishAndNavigate = useCallback((errorMessage?: string) => {
    if (onCompleteCalledRef.current) return;
    onCompleteCalledRef.current = true;
    pollingRef.current = false;
    setLoading(false);
    if (errorMessage) {
      showToast(errorMessage, 'error');
    }
    timeoutRef.current = setTimeout(() => {
      onComplete();
    }, 100);
  }, [onComplete, showToast]);

  const pollRebuildProgress = async (taskId: string) => {
    pollingRef.current = true;
    retryCountRef.current = 0;

    while (pollingRef.current) {
      try {
        const result = await api.getRebuildProgress(taskId);
        retryCountRef.current = 0;

        setProgress(result.progress ?? 0);

        if (result.status === 'done') {
          finishAndNavigate();
          return;
        }

        if (result.status === 'error') {
          finishAndNavigate(t('welcome.rebuildFailed'));
          return;
        }

        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
      } catch (error) {
        retryCountRef.current++;
        if (retryCountRef.current > MAX_RETRY_COUNT) {
          console.error('Poll rebuild progress failed after retries:', error);
          finishAndNavigate(t('welcome.rebuildFailed'));
          return;
        }
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL * 2));
      }
    }
  };

  const handleSelect = async () => {
    if (loading) return;
    setLoading(true);
    setProgress(0);
    setProgressMessage(t('welcome.selectingFolder'));
    try {
      const result = await api.changeAlbumPath();
      if (result.task_id) {
        setProgressMessage(t('welcome.buildingIndex'));
        pollRebuildProgress(result.task_id);
      } else {
        finishAndNavigate();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'welcome.selectFailed';
      if (message !== 'welcome.folderNotSelected') {
        showToast(t(message), 'error');
      }
      setLoading(false);
      pollingRef.current = false;
    }
  };

  useEffect(() => {
    return () => {
      pollingRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center w-full h-full bg-page">
      <div className="max-w-md text-center space-y-6">
        <div className="text-6xl">📷</div>

        <div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">{t('welcome.title')}</h1>
          <p className="text-sm text-text-secondary">{t('welcome.subtitle')}</p>
        </div>

        <p className="text-sm text-text-secondary leading-relaxed">{t('welcome.description')}</p>

        {loading && (
          <div className="space-y-2">
            <div className="w-full h-2 bg-border rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-text-secondary">{progressMessage}</p>
          </div>
        )}

        <button
          onClick={handleSelect}
          disabled={loading}
          className="w-full py-3 bg-primary text-white rounded-lg font-medium text-sm hover:bg-primary-hover disabled:opacity-50 transition-all"
        >
          {loading ? `${t('welcome.processing')} ${progress}%` : t('welcome.selectAlbum')}
        </button>

        <p className="text-xs text-text-tertiary">{t('welcome.hint')}</p>
      </div>
    </div>
  );
}
