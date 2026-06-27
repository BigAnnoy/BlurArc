import { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { useToast } from '../common/Toast';
import { api } from '../../services/api';
import { useI18n } from '../../contexts/I18nContext';
import type { Settings } from '../../types';

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onDataRefresh?: () => void;
}

export function SettingsDialog({ isOpen, onClose, onDataRefresh }: SettingsDialogProps) {
  const { showToast } = useToast();
  const { t, setLanguage } = useI18n();
  const [settings, setSettings] = useState<Settings>({
    albumPath: '',
    theme: 'system',
    language: 'zh',
  });
  const [loading, setLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildProgress, setRebuildProgress] = useState(0);
  const [rebuildMessage, setRebuildMessage] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    try {
      const res = await api.getSettings();
      setSettings({
        albumPath: res.album_path || '',
        theme: (res.theme as Settings['theme']) || 'system',
        language: (res.language as Settings['language']) || 'zh',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '加载设置失败';
      showToast(message, 'error');
    }
  };

  const handleThemeChange = async (theme: string) => {
    setSettings((prev) => ({ ...prev, theme: theme as Settings['theme'] }));
    try {
      await api.updateSettings({ theme });
      localStorage.setItem('theme', theme);
      // Apply theme
      const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const isDark = theme === 'dark' || (theme === 'system' && systemPrefersDark);
      document.documentElement.classList.toggle('dark', isDark);
      showToast('主题已更改', 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : '更改主题失败';
      showToast(message, 'error');
    }
  };

  const handleLanguageChange = async (language: string) => {
    setSettings((prev) => ({ ...prev, language: language as Settings['language'] }));
    try {
      await api.updateSettings({ language });
      setLanguage(language as 'zh' | 'en');
      showToast(t('settings.languageChanged'), 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : t('settings.languageChangeFailed');
      showToast(message, 'error');
    }
  };

  const handleChangeAlbumPath = async () => {
    try {
      const res = await api.changeAlbumPath();
      setSettings((prev) => ({ ...prev, albumPath: res.album_path }));
      showToast('相册路径已更改，正在重建索引...', 'info');

      // 开始轮询重建进度
      setRebuilding(true);
      setRebuildProgress(0);
      setRebuildMessage('正在启动重建...');

      const pollProgress = async () => {
        try {
          const progress = await api.getRebuildProgress(res.task_id);
          setRebuildProgress(progress.progress);
          setRebuildMessage(progress.message);

          if (progress.status === 'running') {
            setTimeout(pollProgress, 500);
          } else if (progress.status === 'done') {
            setRebuilding(false);
            showToast('索引重建完成', 'success');
            // 刷新预览内容
            if (onDataRefresh) {
              onDataRefresh();
            }
          } else if (progress.status === 'error') {
            setRebuilding(false);
            showToast(`重建失败: ${progress.message}`, 'error');
          }
        } catch (error) {
          setRebuilding(false);
          showToast('查询进度失败', 'error');
        }
      };
      pollProgress();
    } catch (error) {
      const message = error instanceof Error ? error.message : '更改相册路径失败';
      showToast(message, 'error');
    }
  };

  const handleClearCache = async () => {
    setLoading(true);
    try {
      const res = await api.clearCache();
      showToast(`已清空缓存，释放 ${res.freed_mb.toFixed(1)} MB`, 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : '清空缓存失败';
      showToast(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRebuildIndex = async () => {
    setRebuilding(true);
    setRebuildProgress(0);
    setRebuildMessage('正在启动重建...');
    try {
      const res = await api.rebuildIndex();
      const taskId = res.task_id;
      showToast(`已清空 ${res.cache_cleared} 个缩略图，开始重建索引`, 'info');

      // 轮询进度
      const pollProgress = async () => {
        try {
          const progress = await api.getRebuildProgress(taskId);
          setRebuildProgress(progress.progress);
          setRebuildMessage(progress.message);

          if (progress.status === 'running') {
            setTimeout(pollProgress, 500);
          } else if (progress.status === 'done') {
            setRebuilding(false);
            showToast('索引重建完成', 'success');
          } else if (progress.status === 'error') {
            setRebuilding(false);
            showToast(`重建失败: ${progress.message}`, 'error');
          }
        } catch (error) {
          setRebuilding(false);
          showToast('查询进度失败', 'error');
        }
      };
      pollProgress();
    } catch (error) {
      const message = error instanceof Error ? error.message : '重建索引失败';
      showToast(message, 'error');
      setRebuilding(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('settings.title')}
      footer={
        <button onClick={onClose} className="px-4 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-all">
          {t('common.close')}
        </button>
      }
    >
      <div className="space-y-6 p-5">
        <div>
          <label className="block text-sm font-medium mb-2">{t('settings.albumPath')}</label>
          <div className="flex gap-3">
            <input
              type="text"
              value={settings.albumPath}
              readOnly
              className="flex-1 px-3 py-2 border border-border rounded-md text-sm bg-page"
            />
            <button
              onClick={handleChangeAlbumPath}
              className="px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary transition-all"
            >
              {t('settings.change')}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">{t('settings.theme')}</label>
          <select
            value={settings.theme}
            onChange={(e) => handleThemeChange(e.target.value)}
            className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:border-primary bg-card"
          >
            <option value="system">{t('settings.themeSystem')}</option>
            <option value="light">{t('settings.themeLight')}</option>
            <option value="dark">{t('settings.themeDark')}</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">{t('settings.language')}</label>
          <select
            value={settings.language}
            onChange={(e) => handleLanguageChange(e.target.value)}
            className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:border-primary bg-card"
          >
            <option value="zh">{t('settings.languageZh')}</option>
            <option value="en">{t('settings.languageEn')}</option>
          </select>
        </div>

        <div className="pt-4 border-t border-border space-y-3">
          <button
            onClick={handleRebuildIndex}
            disabled={rebuilding || loading}
            className="w-full px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary disabled:opacity-50 transition-all"
          >
            {rebuilding ? `${t('settings.rebuilding')} ${rebuildProgress}%` : t('settings.rebuildIndex')}
          </button>
          {rebuilding && (
            <div className="text-xs text-text-secondary text-center">{rebuildMessage}</div>
          )}
          <button
            onClick={handleClearCache}
            disabled={loading || rebuilding}
            className="w-full px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary disabled:opacity-50 transition-all"
          >
            {loading ? t('settings.clearing') : t('settings.clearCache')}
          </button>
        </div>
      </div>
    </Modal>
  );
}
