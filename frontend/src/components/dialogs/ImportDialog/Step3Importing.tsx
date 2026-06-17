import { useI18n } from '../../../contexts/I18nContext';
import type { ImportProgress } from './types';

interface Step3ImportingProps {
  progress: ImportProgress;
  isPaused: boolean;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onClose: () => void;
}

export function Step3Importing({
  progress,
  isPaused,
  onPause,
  onResume,
  onCancel,
  onClose,
}: Step3ImportingProps) {
  const { t } = useI18n();

  // 进度百分比：直接使用后端计算的 progress 字段
  const percent = progress.progress ?? 0;
  const isCompleted = progress.status === 'completed' || progress.status === 'done';
  const isFailed = progress.status === 'failed' || progress.status === 'error';
  const isCancelled = progress.status === 'cancelled';
  // 终态：completed / failed / cancelled — 任何一个都意味着导入流程结束
  const isFinalState = isCompleted || isFailed || isCancelled;
  // paused：用后端状态 + 前端状态合并（以状态为准，前端状态只是个快捷标记）
  const actuallyPaused = progress.status === 'paused' || isPaused;

  return (
    <div className="space-y-4">
      {/* 进度条 */}
      <div className="space-y-2">
        <div className="h-3 bg-page rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              isFailed ? 'bg-red-500' : isCompleted ? 'bg-green-500' : isCancelled ? 'bg-gray-400' : 'bg-primary'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">
            {isCompleted
              ? t('importing.complete')
              : isFailed
              ? t('importing.failed')
              : isCancelled
              ? t('importing.cancelled')
              : actuallyPaused
              ? t('importing.paused')
              : progress.status === 'scanning'
              ? t('importing.scanning')
              : progress.status === 'pending'
              ? t('importing.starting')
              : `${t('importing.importing')}: ${progress.current}`}
          </span>
          <span className="font-mono">{percent}%</span>
        </div>
      </div>

      {/* 详细信息 */}
      <div className="text-center space-y-1">
        <div className="font-mono text-3xl">{percent}%</div>
        <div className="text-sm text-text-secondary">
          {t('importing.files', { current: progress.step, total: progress.total })}
        </div>
      </div>

      {/* 导入结果明细（完成或失败时显示） */}
      {(isCompleted || isFailed) && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 bg-page rounded-lg text-sm">
          <div className="text-center">
            <div className="text-text-secondary text-xs">{t('importing.resultImported')}</div>
            <div className="font-mono text-lg text-green-600">{progress.step}</div>
          </div>
          <div className="text-center">
            <div className="text-text-secondary text-xs">{t('importing.resultDuplicated')}</div>
            <div className="font-mono text-lg text-yellow-600">{progress.duplicated ?? 0}</div>
          </div>
          <div className="text-center">
            <div className="text-text-secondary text-xs">{t('importing.resultFailed')}</div>
            <div className={`font-mono text-lg ${(progress.failed ?? 0) > 0 ? 'text-red-600' : 'text-text-secondary'}`}>
              {progress.failed ?? 0}
            </div>
          </div>
          <div className="text-center">
            <div className="text-text-secondary text-xs">{t('importing.resultTotal')}</div>
            <div className="font-mono text-lg">{progress.total}</div>
          </div>
        </div>
      )}

      {/* 错误信息 */}
      {isFailed && progress.error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <div className="font-medium mb-1">{t('importing.importFailed')}</div>
          <div className="text-red-600">{progress.error}</div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex justify-center gap-3 pt-4">
        {/* 终态：只显示关闭按钮 */}
        {isFinalState && (
          <button
            onClick={onClose}
            className="px-4 py-2 bg-page border border-border rounded-md text-sm hover:border-primary transition-all"
          >
            {t('importing.close')}
          </button>
        )}
        {/* 非终态：显示暂停/继续 + 取消 */}
        {!isFinalState && (
          <>
            {actuallyPaused ? (
              <button
                onClick={onResume}
                className="px-4 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-all"
              >
                {t('importing.resume')}
              </button>
            ) : (
              <button
                onClick={onPause}
                className="px-4 py-2 bg-yellow-500 text-white rounded-md text-sm hover:bg-yellow-600 transition-all"
              >
                {t('importing.pause')}
              </button>
            )}
            <button
              onClick={onCancel}
              className="px-4 py-2 bg-red-500 text-white rounded-md text-sm hover:bg-red-600 transition-all"
            >
              {t('importing.cancel')}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
