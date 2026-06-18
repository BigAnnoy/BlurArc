import { useState, useEffect, useCallback } from 'react';
import { Modal } from '../../common/Modal';
import { useToast } from '../../common/Toast';
import { useI18n } from '../../../contexts/I18nContext';
import { api } from '../../../services/api';
import { Step1Select } from './Step1Select';
import { Step2Preview } from './Step2Preview';
import { Step3Importing } from './Step3Importing';
import { PhotoPreviewModal } from './PhotoPreviewModal';
import { ImportModeDialog } from './ImportModeDialog';
import type { ImportStep, ImportMode, CheckResult, CheckProgress, ImportProgress, ImportPhoto } from './types';
import { PhoneImportPanel } from './PhoneImportPanel';

interface ImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

export function ImportDialog({ isOpen, onClose, onComplete }: ImportDialogProps) {
  const { t } = useI18n();
  const { showToast } = useToast();

  // 步骤控制
  const [step, setStep] = useState<ImportStep>('select-mode');

  // 步骤1：选择
  const [sourcePath, setSourcePath] = useState('');
  const [checkId, setCheckId] = useState<string | null>(null);
  const [checkProgress, setCheckProgress] = useState<CheckProgress>({
    status: 'queued',
    progress: 0,
    stage: 'queued',
    detail: '',
  });

  // 步骤2：预览
  const [previewData, setPreviewData] = useState<CheckResult | null>(null);

  // 步骤3：导入
  const [importId, setImportId] = useState<string | null>(null);
  const [importProgress, setImportProgress] = useState<ImportProgress>({
    step: 0,
    total: 0,
    current: '',
    status: 'idle',
  });
  const [isPaused, setIsPaused] = useState(false);
  // 终态守卫：completed/failed/cancelled 一旦处理过就不再触发 toast 和回调
  const [finalStatus, setFinalStatus] = useState<string | null>(null);

  // 照片预览
  const [previewPhoto, setPreviewPhoto] = useState<ImportPhoto | null>(null);

  // 导入模式选择弹窗
  const [showModeDialog, setShowModeDialog] = useState(false);

  // 记录用户是从哪个步骤进入 checking 的（用于预览页面的返回按钮）
  const [sourceStep, setSourceStep] = useState<ImportStep>('select-mode');

  // 重置状态
  const resetState = useCallback(() => {
    setStep('select-mode');
    setSourcePath('');
    setCheckId(null);
    setCheckProgress({ status: 'queued', progress: 0, stage: 'queued', detail: '' });
    setPreviewData(null);
    setImportId(null);
    setImportProgress({ step: 0, total: 0, current: '', status: 'idle' });
    setIsPaused(false);
    setFinalStatus(null);
    setSourceStep('select-mode');
    setPreviewPhoto(null);
    setShowModeDialog(false);
  }, []);

  // 弹窗打开时重置
  useEffect(() => {
    if (isOpen) {
      resetState();
    }
  }, [isOpen, resetState]);

  // 检查进度轮询
  useEffect(() => {
    if (step !== 'checking' || !checkId) return;

    const interval = setInterval(async () => {
      try {
        const progress = await api.getImportCheckProgress(checkId);
        setCheckProgress(progress);

        if (progress.status === 'completed' && progress.result) {
          clearInterval(interval);
          setPreviewData(progress.result);
          setStep('preview');
        } else if (progress.status === 'failed') {
          clearInterval(interval);
          showToast(`${t('import.checkFailed')}: ${progress.detail}`, 'error');
          setStep('select-mode');
        } else if (progress.status === 'cancelled') {
          clearInterval(interval);
          setStep('select-mode');
        }
      } catch (error) {
        console.error('Failed to get check progress:', error);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [step, checkId, showToast, t]);

  // 导入进度轮询
  useEffect(() => {
    if (step !== 'importing' || !importId || finalStatus) return;

    const interval = setInterval(async () => {
      try {
        const progress = await api.getImportProgressById(importId);
        setImportProgress(progress);

        if (finalStatus) return;

        if (progress.status === 'completed' || progress.status === 'done') {
          setFinalStatus('completed');
          clearInterval(interval);
          showToast(t('importing.complete'), 'success');
          if (sourceStep === 'phone-upload') {
            api.discardPhoneSession().catch(() => {});
          }
          onComplete();
        } else if (progress.status === 'failed' || progress.status === 'error') {
          setFinalStatus('failed');
          clearInterval(interval);
          showToast(`${t('importing.importFailed')}: ${progress.error || t('preview.unknown')}`, 'error');
        } else if (progress.status === 'cancelled') {
          setFinalStatus('cancelled');
          clearInterval(interval);
          showToast(t('importing.cancelled'), 'info');
          onClose();
        }
      } catch (error) {
        console.error('Failed to get import progress:', error);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [step, importId, finalStatus, onComplete, onClose, showToast, t]);

  // 开始检查（从手机导入直接传入 sourcePath）
  const handleStartCheckFromPhone = async (phoneSourcePath: string) => {
    setSourcePath(phoneSourcePath);
    setSourceStep('phone-upload');
    setStep('checking');
    setCheckProgress({ status: 'queued', progress: 0, stage: 'queued', detail: t('import.checkingStatus') });

    try {
      const res = await api.startImportCheck(phoneSourcePath);
      setCheckId(res.check_id);
    } catch (error) {
      const message = error instanceof Error ? error.message : t('import.startCheckFailed');
      showToast(message, 'error');
      setStep('select-mode');
    }
  };

  // 开始检查
  const handleStartCheck = async () => {
    if (!sourcePath.trim()) {
      showToast(t('import.enterPathFirst'), 'error');
      return;
    }

    setSourceStep('select-path');
    setStep('checking');
    setCheckProgress({ status: 'queued', progress: 0, stage: 'queued', detail: t('import.checkingStatus') });

    try {
      const res = await api.startImportCheck(sourcePath);
      setCheckId(res.check_id);
    } catch (error) {
      const message = error instanceof Error ? error.message : t('import.startCheckFailed');
      showToast(message, 'error');
      setStep('select-mode');
    }
  };

  // 取消检查
  const handleCancelCheck = () => {
    setCheckId(null);
    setStep('select-mode');
    setCheckProgress({ status: 'cancelled', progress: 0, stage: 'queued', detail: t('import.cancelled') });
  };

  // 开始导入 - 先显示模式选择对话框
  const handleStartImport = async () => {
    if (!previewData) return;
    // 手机导入源文件在临时目录，不需要用户选择 copy/move，直接走 move
    if (sourceStep === 'phone-upload') {
      await startImportWithMode('move');
    } else {
      setShowModeDialog(true);
    }
  };

  // 导入实际执行
  const startImportWithMode = async (mode: ImportMode) => {
    try {
      const settings = await api.getSettings();
      const targetPath = settings.album_path;
      if (!targetPath) {
        showToast(t('settings.albumPathChangeFailed'), 'error');
        return;
      }
      const res = await api.startImport(sourcePath, targetPath, mode);
      setImportId(res.import_id);
      setStep('importing');
      setImportProgress({ step: 0, total: previewData?.media_count || 0, current: '', status: 'pending' });
      // 导入已启动，手机临时文件等导入完成后清理（见导入进度轮询）
    } catch (error) {
      const message = error instanceof Error ? error.message : t('importing.startFailed');
      showToast(message, 'error');
    }
  };

  // 处理模式选择
  const handleModeSelect = async (selectedMode: ImportMode) => {
    setShowModeDialog(false);
    await startImportWithMode(selectedMode);
  };

  // 暂停导入
  const handlePauseImport = async () => {
    if (!importId) return;
    try {
      await api.pauseImport(importId);
      setIsPaused(true);
    } catch (error) {
      console.error('Failed to pause import:', error);
    }
  };

  // 继续导入
  const handleResumeImport = async () => {
    if (!importId) return;
    try {
      await api.resumeImport(importId);
      setIsPaused(false);
    } catch (error) {
      console.error('Failed to resume import:', error);
    }
  };

  // 取消导入
  const handleCancelImport = async () => {
    if (!importId) {
      onClose();
      return;
    }

    if (!window.confirm(t('importing.cancelConfirm'))) return;

    try {
      await api.cancelImport(importId);
      // 不弹 toast / 不关闭：让轮询检测到 cancelled 状态后统一处理（避免双弹）
    } catch (error) {
      console.error('Failed to cancel import:', error);
      showToast(t('importing.cancelFailed'), 'error');
      onClose();
    }
  };

  // 删除文件（从预览数据中移除）
  const handleDeleteFiles = async (paths: string[]) => {
    if (paths.length === 0) return;

    try {
      // 获取源文件夹路径，用于删除源文件夹中的重复文件
      const sourcePaths = previewData?.source_path ? [previewData.source_path] : undefined;
      await api.deletePhotos(paths, sourcePaths);
      showToast(t('importing.deletedFiles', { count: paths.length }), 'success');

      // 更新预览数据
      if (previewData) {
        const deletedSet = new Set(paths);
        const updatedDateFolders = previewData.date_folders
          .map((folder) => ({
            ...folder,
            files: folder.files.filter((f) => !deletedSet.has(f.path)),
          }))
          .filter((folder) => folder.files.length > 0)
          .map((folder) => ({
            ...folder,
            count: folder.files.length,
            size: folder.files.reduce((sum, f) => sum + (f.size || 0), 0),
          }));

        const updatedTargetDup: Record<string, ImportPhoto[]> = {};
        for (const [hash, files] of Object.entries(previewData.target_duplicates)) {
          const remaining = files.filter((f) => !deletedSet.has(f.path));
          if (remaining.length > 0) {
            updatedTargetDup[hash] = remaining;
          }
        }

        const updatedSourceDup: Record<string, ImportPhoto[]> = {};
        for (const [hash, files] of Object.entries(previewData.source_duplicates)) {
          const remaining = files.filter((f) => !deletedSet.has(f.path));
          if (remaining.length > 0) {
            updatedSourceDup[hash] = remaining;
          }
        }

        // 过滤掉只剩一个文件的重复组（不再是重复）
        const filteredTargetDup: Record<string, ImportPhoto[]> = {};
        for (const [hash, files] of Object.entries(updatedTargetDup)) {
          if (files.length >= 2) {
            filteredTargetDup[hash] = files;
          }
        }

        const filteredSourceDup: Record<string, ImportPhoto[]> = {};
        for (const [hash, files] of Object.entries(updatedSourceDup)) {
          if (files.length >= 2) {
            filteredSourceDup[hash] = files;
          }
        }

        // 计算新的总大小（MB）
        const newTotalSizeMB = updatedDateFolders.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024);

        setPreviewData({
          ...previewData,
          date_folders: updatedDateFolders,
          target_duplicates: filteredTargetDup,
          source_duplicates: filteredSourceDup,
          media_count: updatedDateFolders.reduce((sum, f) => sum + f.count, 0),
          total_size_mb: newTotalSizeMB,
        });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t('delete.failed');
      showToast(message, 'error');
    }
  };

  // 渲染当前步骤
  const renderStep = () => {
    switch (step) {
      case 'select-mode':
        return (
          <div className="space-y-5">
            <p className="text-sm text-text-secondary text-center">{t('phoneImport.selectMode')}</p>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setStep('phone-upload')}
                className="flex flex-col items-center gap-3 p-6 bg-card border-2 border-border rounded-xl hover:border-primary transition-all group"
              >
                <span className="text-4xl">📱</span>
                <div className="text-center">
                  <p className="font-semibold text-sm group-hover:text-primary transition-colors">
                    {t('phoneImport.entry')}
                  </p>
                  <p className="text-xs text-text-tertiary mt-1">
                    {t('phoneImport.subtitle')}
                  </p>
                </div>
              </button>
              <button
                onClick={() => setStep('select-path')}
                className="flex flex-col items-center gap-3 p-6 bg-card border-2 border-border rounded-xl hover:border-primary transition-all group"
              >
                <span className="text-4xl">💻</span>
                <div className="text-center">
                  <p className="font-semibold text-sm group-hover:text-primary transition-colors">
                    {t('phoneImport.localImport')}
                  </p>
                  <p className="text-xs text-text-tertiary mt-1">
                    {t('phoneImport.localImportDesc')}
                  </p>
                </div>
              </button>
            </div>
          </div>
        );

      case 'phone-upload':
        return (
          <PhoneImportPanel
            onStartImport={(uploadDir: string) => {
              setSourcePath(uploadDir);
              handleStartCheckFromPhone(uploadDir);
            }}
            onBack={() => setStep('select-mode')}
          />
        );

      case 'select-path':
      case 'checking':
        return (
          <Step1Select
            sourcePath={sourcePath}
            onSourcePathChange={setSourcePath}
            isChecking={step === 'checking'}
            checkProgress={checkProgress}
            onConfirm={handleStartCheck}
            onCancel={handleCancelCheck}
          />
        );
      case 'preview':
        return (
          <Step2Preview
            previewData={previewData}
            onPreviewPhoto={setPreviewPhoto}
            onDeleteFiles={handleDeleteFiles}
            onStartImport={handleStartImport}
            onBack={() => setStep(sourceStep)}
          />
        );
      case 'importing':
        return (
          <Step3Importing
            progress={importProgress}
            isPaused={isPaused}
            onPause={handlePauseImport}
            onResume={handleResumeImport}
            onCancel={handleCancelImport}
            onClose={onClose}
          />
        );
    }
  };

  // 获取标题
  const getTitle = () => {
    switch (step) {
      case 'select-mode':
      case 'select-path':
        return t('import.title');
      case 'phone-upload':
        return t('phoneImport.title');
      case 'checking':
        return t('import.checking');
      case 'preview':
        return t('import.preview');
      case 'importing':
        return t('import.progress');
    }
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={step === 'importing' ? () => {} : onClose}
        title={getTitle()}
        size={
          step === 'select-mode' || step === 'select-path' || step === 'checking' || step === 'phone-upload'
            ? 'md'
            : step === 'importing'
            ? 'lg'
            : '2xl'
        }
      >
        {renderStep()}
      </Modal>
      <PhotoPreviewModal
        photo={previewPhoto}
        onClose={() => setPreviewPhoto(null)}
      />
      <ImportModeDialog
        isOpen={showModeDialog}
        onClose={() => setShowModeDialog(false)}
        onSelect={handleModeSelect}
      />
    </>
  );
}
