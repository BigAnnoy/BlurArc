import { api } from '../../../services/api';
import { useI18n } from '../../../contexts/I18nContext';
import type { CheckProgress } from './types';
import { getCheckStageText } from './types';

interface Step1SelectProps {
  sourcePath: string;
  onSourcePathChange: (path: string) => void;
  isChecking: boolean;
  checkProgress: CheckProgress;
  onConfirm: () => void;
  onCancel: () => void;
}

export function Step1Select({
  sourcePath,
  onSourcePathChange,
  isChecking,
  checkProgress,
  onConfirm,
  onCancel,
}: Step1SelectProps) {
  const { t } = useI18n();

  const handleBrowse = async () => {
    const path = await api.selectFolder();
    if (path) {
      onSourcePathChange(path);
    } else if (!window.pywebview) {
      // 浏览器环境不支持文件夹浏览，保持输入框可编辑
      console.log('浏览器环境不支持文件夹浏览，请手动输入路径');
    }
  };

  // 确保进度值在 0-100 范围内
  const progressPercent = Math.max(0, Math.min(100, Math.round(checkProgress.progress)));
  const checkStageText = getCheckStageText(t);
  const stageText = checkStageText[checkProgress.stage] || t('common.loading');

  return (
    <div className="space-y-5">
      {/* 源路径输入 */}
      <div>
        <label className="block text-sm font-medium mb-2">{t('import.sourcePath')}</label>
        <div className="flex gap-3">
          <input
            type="text"
            value={sourcePath}
            onChange={(e) => onSourcePathChange(e.target.value)}
            placeholder={t('import.sourcePathPlaceholder')}
            disabled={isChecking}
            className="flex-1 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:border-primary bg-card disabled:opacity-50"
          />
          <button
            onClick={handleBrowse}
            disabled={isChecking}
            className="px-3 py-2 bg-page border border-border rounded-md text-sm hover:border-primary disabled:opacity-50 transition-all"
          >
            📁
          </button>
        </div>
      </div>

      {/* 检查进度 */}
      {isChecking && (
        <div className="space-y-3 p-4 bg-page rounded-lg border border-border">
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-secondary">{stageText}</span>
            <span className="font-mono">{progressPercent}%</span>
          </div>
          <div className="h-2 bg-card rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {checkProgress.detail && (
            <div className="text-xs text-text-tertiary truncate">{checkProgress.detail}</div>
          )}
          <button
            onClick={onCancel}
            className="w-full px-3 py-1.5 bg-card border border-border rounded-md text-sm hover:border-primary transition-all"
          >
            {t('import.cancelCheck')}
          </button>
        </div>
      )}

      {/* 确认按钮 */}
      {!isChecking && (
        <button
          onClick={onConfirm}
          disabled={!sourcePath.trim()}
          className="w-full px-4 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover disabled:opacity-50 transition-all"
        >
          {t('import.confirm')}
        </button>
      )}
    </div>
  );
}
