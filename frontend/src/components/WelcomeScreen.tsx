import { useState } from 'react';
import { useI18n } from '../contexts/I18nContext';
import { useToast } from './common/Toast';
import { api } from '../services/api';

interface WelcomeScreenProps {
  onComplete: () => void;
}

export function WelcomeScreen({ onComplete }: WelcomeScreenProps) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleSelect = async () => {
    setLoading(true);
    try {
      await api.changeAlbumPath();
      onComplete();
    } catch (error) {
      const message = error instanceof Error ? error.message : t('welcome.selectFailed');
      // Only show toast if user didn't cancel the dialog
      if (message !== '未选择文件夹') {
        showToast(message, 'error');
      }
    } finally {
      setLoading(false);
    }
  };

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

        {/* Action button */}
        <button
          onClick={handleSelect}
          disabled={loading}
          className="w-full py-3 bg-primary text-white rounded-lg font-medium text-sm hover:bg-primary-hover disabled:opacity-50 transition-all"
        >
          {loading ? t('welcome.selecting') : t('welcome.selectAlbum')}
        </button>

        {/* Hint */}
        <p className="text-xs text-text-tertiary">{t('welcome.hint')}</p>
      </div>
    </div>
  );
}
