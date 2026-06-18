import { useState, useEffect, useRef } from 'react';
import { useI18n } from '../contexts/I18nContext';
import { useToast } from './common/Toast';
import { api } from '../services/api';

interface WelcomeScreenProps {
  onComplete: () => void;
}

// 轮询配置
const POLL_INTERVAL = 500; // 轮询间隔 ms
const MAX_POLL_TIME = 5 * 60 * 1000; // 最大轮询时间 5 分钟
const MAX_RETRY_COUNT = 3; // 网络错误最大重试次数

export function WelcomeScreen({ onComplete }: WelcomeScreenProps) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const pollingRef = useRef<boolean>(false);
  const startTimeRef = useRef<number>(0);
  const retryCountRef = useRef<number>(0);

  // 轮询索引重建进度
  const pollRebuildProgress = async (taskId: string) => {
    pollingRef.current = true;
    startTimeRef.current = Date.now();
    retryCountRef.current = 0;

    while (pollingRef.current) {
      // 检查超时
      if (Date.now() - startTimeRef.current > MAX_POLL_TIME) {
        pollingRef.current = false;
        setLoading(false);
        showToast(t('welcome.rebuildFailed'), 'error');
        return;
      }

      try {
        const result = await api.getRebuildProgress(taskId);
        retryCountRef.current = 0; // 成功后重置重试计数
        
        setProgress(result.progress ?? 0);
        setProgressMessage(result.message ?? '');
        
        if (result.status === 'done') {
          pollingRef.current = false;
          setLoading(false);
          onComplete();
          return;
        }
        
        if (result.status === 'error') {
          pollingRef.current = false;
          setLoading(false);
          showToast(t('welcome.rebuildFailed'), 'error');
          return;
        }
        
        // 继续轮询
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
      } catch (error) {
        retryCountRef.current++;
        if (retryCountRef.current > MAX_RETRY_COUNT) {
          console.error('Poll rebuild progress failed after retries:', error);
          pollingRef.current = false;
          setLoading(false);
          showToast(t('welcome.rebuildFailed'), 'error');
          return;
        }
        // 重试前等待
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL * 2));
      }
    }
  };

  const handleSelect = async () => {
    setLoading(true);
    setProgress(0);
    setProgressMessage(t('welcome.selectingFolder'));
    try {
      const result = await api.changeAlbumPath();
      if (result.task_id) {
        setProgressMessage(t('welcome.buildingIndex'));
        await pollRebuildProgress(result.task_id);
      } else {
        // 没有 task_id，直接完成
        setLoading(false);
        onComplete();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t('welcome.selectFailed');
      // Only show toast if user didn't cancel the dialog
      if (message !== t('welcome.folderNotSelected')) {
        showToast(message, 'error');
      }
      setLoading(false);
      pollingRef.current = false;
    }
  };

  // 组件卸载时停止轮询
  useEffect(() => {
    return () => {
      pollingRef.current = false;
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center w-full h-full bg-page">
      <div className="max-w-md text-center space-y-6">
        {/* Icon */}
        <div className="text-6xl">📷</div>

        {/* Title */}
        <div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">{t('welcome.title')}</h1>
          <p className="text-sm text-text-secondary">{t('welcome.subtitle')}</p>
        </div>

        {/* Description */}
        <p className="text-sm text-text-secondary leading-relaxed">{t('welcome.description')}</p>

        {/* Progress indicator */}
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

        {/* Action button */}
        <button
          onClick={handleSelect}
          disabled={loading}
          className="w-full py-3 bg-primary text-white rounded-lg font-medium text-sm hover:bg-primary-hover disabled:opacity-50 transition-all"
        >
          {loading ? `${t('welcome.processing')} ${progress}%` : t('welcome.selectAlbum')}
        </button>

        {/* Hint */}
        <p className="text-xs text-text-tertiary">{t('welcome.hint')}</p>
      </div>
    </div>
  );
}
